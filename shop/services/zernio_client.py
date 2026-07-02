import json
import logging
import time
from datetime import datetime, timezone
from typing import Any

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)


class ZernioRateLimitError(RuntimeError):
    def __init__(self, retry_after: int, message: str) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class ZernioClient:
    """Zernio.com — Instagram DM va izohlar (Meta Developer shart emas)."""

    _last_request_at: float = 0.0

    def __init__(self) -> None:
        self.api_key = settings.ZERNIO_API_KEY
        self.base_url = settings.ZERNIO_API_URL.rstrip("/")
        self.account_id = settings.ZERNIO_ACCOUNT_ID
        self.timeout = httpx.Timeout(30.0, connect=10.0)
        self._account_cache: dict[str, Any] | None = None
        self._min_interval = settings.ZERNIO_MIN_REQUEST_INTERVAL_SECONDS
        self._max_retries = settings.ZERNIO_RATE_LIMIT_MAX_RETRIES

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _throttle(self) -> None:
        elapsed = time.monotonic() - ZernioClient._last_request_at
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        ZernioClient._last_request_at = time.monotonic()

    def _parse_retry_after(self, response: httpx.Response) -> int:
        try:
            data = response.json()
            return int(data.get("details", {}).get("retryAfterSeconds", 7))
        except (json.JSONDecodeError, TypeError, ValueError):
            return 7

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
        json: dict | None = None,
    ) -> Any:
        url = f"{self.base_url}{path}"

        for attempt in range(self._max_retries):
            self._throttle()
            with httpx.Client(timeout=self.timeout) as client:
                response = client.request(
                    method,
                    url,
                    headers=self._headers(),
                    params=params,
                    json=json,
                )

            if response.status_code == 429:
                retry_after = self._parse_retry_after(response)
                if attempt + 1 >= self._max_retries:
                    raise ZernioRateLimitError(
                        retry_after,
                        f"Zernio rate limit ({retry_after}s kutish kerak)",
                    )
                logger.warning(
                    "Zernio rate limit — %ds kutib qayta uriniladi (%d/%d)",
                    retry_after,
                    attempt + 1,
                    self._max_retries,
                )
                time.sleep(retry_after + 1)
                continue

            if response.status_code >= 400:
                detail = response.text[:300]
                raise RuntimeError(f"Zernio API {response.status_code}: {detail}")

            if not response.content:
                return {}
            return response.json()

        raise RuntimeError("Zernio API so'rovi muvaffaqiyatsiz")

    def resolve_account_id(self) -> str:
        if self.account_id:
            return self.account_id

        data = self._request("GET", "/accounts")
        accounts = data.get("accounts") or []
        for account in accounts:
            if account.get("platform") == "instagram" and account.get("isActive"):
                self.account_id = account["_id"]
                self._account_cache = account
                return self.account_id

        raise RuntimeError(
            "Zernio da Instagram akkaunt ulanmagan. "
            "https://zernio.com/dashboard da Instagram ni ulang."
        )

    def get_account_info(self) -> dict[str, Any]:
        if self._account_cache:
            account = self._account_cache
        else:
            account_id = self.resolve_account_id()
            data = self._request("GET", "/accounts")
            account = next(
                (a for a in data.get("accounts", []) if a.get("_id") == account_id),
                None,
            )
            if not account:
                raise RuntimeError("Zernio Instagram akkaunt topilmadi")
            self._account_cache = account

        meta = account.get("metadata", {}).get("profileData", {})
        return {
            "username": account.get("username") or meta.get("username", ""),
            "full_name": account.get("displayName") or meta.get("displayName", ""),
            "user_id": str(account.get("platformUserId") or meta.get("id", "")),
            "is_business": meta.get("accountType") == "BUSINESS",
            "account_id": account["_id"],
        }

    def list_conversations(self, limit: int | None = None) -> list[dict[str, Any]]:
        account_id = self.resolve_account_id()
        if limit is None:
            limit = settings.INSTAGRAM_CONVERSATION_LIMIT
        data = self._request(
            "GET",
            "/inbox/conversations",
            params={"accountId": account_id, "limit": limit},
        )
        return data.get("data") or []

    def list_conversation_messages(
        self,
        conversation_id: str,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Barcha sahifalarni o'qiydi (API eng eskidan boshlab qaytaradi)."""
        account_id = self.resolve_account_id()
        if limit is None:
            limit = settings.INSTAGRAM_MESSAGE_FETCH_LIMIT
        page_size = min(limit, settings.INSTAGRAM_MESSAGE_FETCH_LIMIT)
        max_pages = settings.INSTAGRAM_MESSAGE_MAX_PAGES

        all_messages: list[dict[str, Any]] = []
        cursor: str | None = None

        for _ in range(max_pages):
            params: dict[str, Any] = {"accountId": account_id, "limit": page_size}
            if cursor:
                params["cursor"] = cursor
            data = self._request(
                "GET",
                f"/inbox/conversations/{conversation_id}/messages",
                params=params,
            )
            page = data.get("messages") or []
            all_messages.extend(page)
            pagination = data.get("pagination") or {}
            if not pagination.get("hasMore"):
                break
            cursor = pagination.get("nextCursor")
            if not cursor:
                break

        return all_messages

    def send_direct_message(self, conversation_id: str, text: str) -> None:
        account_id = self.resolve_account_id()
        self._request(
            "POST",
            f"/inbox/conversations/{conversation_id}/messages",
            json={"accountId": account_id, "message": text},
        )

    def list_posts_with_comments(self, limit: int | None = None) -> list[dict[str, Any]]:
        account_id = self.resolve_account_id()
        if limit is None:
            limit = settings.INSTAGRAM_MEDIA_AMOUNT
        data = self._request(
            "GET",
            "/inbox/comments",
            params={"accountId": account_id, "limit": limit, "minComments": 1},
        )
        return data.get("data") or []

    def list_post_comments(self, post_id: str, limit: int = 15) -> list[dict[str, Any]]:
        account_id = self.resolve_account_id()
        data = self._request(
            "GET",
            f"/inbox/comments/{post_id}",
            params={"accountId": account_id, "limit": limit},
        )
        return data.get("comments") or []

    def reply_to_comment(
        self,
        post_id: str,
        comment_id: str,
        text: str,
        username: str = "",
    ) -> None:
        account_id = self.resolve_account_id()
        reply = f"@{username} {text}" if username else text
        self._request(
            "POST",
            f"/inbox/comments/{post_id}",
            json={
                "accountId": account_id,
                "message": reply,
                "commentId": comment_id,
            },
        )

    @staticmethod
    def parse_message_time(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            return None
