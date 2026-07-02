import logging
from datetime import datetime, timezone
from typing import Any

from django.conf import settings

from shop.services.zernio_client import ZernioClient

logger = logging.getLogger(__name__)


class InstagramClient:
    """Instagram — Zernio API orqali (Meta Developer / instagrapi shart emas)."""

    _shared_zernio: ZernioClient | None = None
    _ready = False
    _baseline_dm_ids: set[str] | None = None
    _baseline_comment_ids: set[str] | None = None
    _baseline_at: datetime | None = None

    def __init__(self) -> None:
        self.zernio = self._get_zernio()

    @classmethod
    def _get_zernio(cls) -> ZernioClient:
        if cls._shared_zernio is None:
            cls._shared_zernio = ZernioClient()
        return cls._shared_zernio

    @property
    def is_configured(self) -> bool:
        return self.zernio.is_configured

    @property
    def has_session(self) -> bool:
        return self.is_configured and InstagramClient._ready

    def can_auto_connect(self) -> bool:
        return self.is_configured

    def login(self, force_password: bool = False, session_only: bool | None = None) -> None:
        if InstagramClient._ready:
            return
        info = self.zernio.get_account_info()
        InstagramClient._ready = True
        logger.info("Zernio Instagram ulandi: @%s", info["username"])

    def ensure_login(self) -> None:
        if not InstagramClient._ready:
            self.login()

    @staticmethod
    def _parse_created_at(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None

    def establish_baseline(self) -> None:
        """Ishga tushganda mavjud xabarlar — ularga javob berilmaydi."""
        self.ensure_login()
        InstagramClient._baseline_at = datetime.now(timezone.utc)
        dm_ids: set[str] = set()
        comment_ids: set[str] = set()
        fetch_limit = settings.INSTAGRAM_MESSAGE_FETCH_LIMIT

        for conversation in self.zernio.list_conversations():
            conversation_id = conversation["id"]
            raw_messages = self.zernio.list_conversation_messages(conversation_id, limit=fetch_limit)
            for msg in raw_messages:
                if msg.get("direction") == "incoming":
                    dm_ids.add(str(msg["id"]))

        for post in self.zernio.list_posts_with_comments(limit=settings.INSTAGRAM_MEDIA_AMOUNT):
            post_id = post["id"]
            for comment in self.zernio.list_post_comments(post_id):
                comment_ids.add(str(comment["id"]))

        InstagramClient._baseline_dm_ids = dm_ids
        InstagramClient._baseline_comment_ids = comment_ids
        logger.info(
            "Instagram baseline: %d ta DM, %d ta izoh, vaqt=%s (eski xabarlarga javob yo'q)",
            len(dm_ids),
            len(comment_ids),
            InstagramClient._baseline_at.isoformat(),
        )

    @classmethod
    def is_baseline_ready(cls) -> bool:
        return cls._baseline_dm_ids is not None

    def _is_new_dm(self, message_id: str, created_at: str | None = None) -> bool:
        if InstagramClient._baseline_dm_ids is None:
            return False
        if message_id in InstagramClient._baseline_dm_ids:
            return False
        msg_time = self._parse_created_at(created_at)
        baseline_at = InstagramClient._baseline_at
        if msg_time and baseline_at and msg_time >= baseline_at:
            return True
        return True

    def _is_new_comment(self, comment_id: str) -> bool:
        if InstagramClient._baseline_comment_ids is None:
            return False
        return comment_id not in InstagramClient._baseline_comment_ids

    @staticmethod
    def _find_url_in_data(data: Any, depth: int = 0) -> str | None:
        if depth > 8:
            return None
        if isinstance(data, str):
            lower = data.lower()
            if data.startswith("http") and any(
                token in lower
                for token in ("fbsbx", "cdninstagram", "lookaside", ".jpg", ".jpeg", ".png", ".webp")
            ):
                return data
            return None
        if isinstance(data, dict):
            for key in ("url", "imageUrl", "image_url", "mediaUrl", "previewUrl", "src", "attachmentUrl"):
                value = data.get(key)
                if isinstance(value, str) and value.startswith("http"):
                    return value
            for value in data.values():
                found = InstagramClient._find_url_in_data(value, depth + 1)
                if found:
                    return found
        if isinstance(data, list):
            for item in data:
                found = InstagramClient._find_url_in_data(item, depth + 1)
                if found:
                    return found
        return None

    def _extract_message_content(self, msg: dict[str, Any]) -> tuple[str, str | None]:
        text = (msg.get("message") or msg.get("text") or "").strip()
        image_url = self._find_url_in_data(msg)
        if image_url:
            return text, image_url
        return text, None

    def find_conversation_for_user(self, user_id: str) -> str | None:
        if not user_id:
            return None
        for conversation in self.zernio.list_conversations():
            participants = conversation.get("participants") or []
            for participant in participants:
                if str(participant.get("id", "")) == user_id:
                    return str(conversation["id"])
        return None

    def send_direct_to_user(
        self,
        user_id: str,
        text: str,
        *,
        image_url: str | None = None,
    ) -> None:
        thread_id = self.find_conversation_for_user(user_id)
        if not thread_id:
            raise RuntimeError("Foydalanuvchi bilan DM suhbati topilmadi")
        self.send_direct_reply(thread_id, text, image_url=image_url)

    def fetch_new_direct_messages(self) -> list[dict[str, Any]]:
        if not self.is_baseline_ready():
            logger.warning("Instagram baseline hali o'rnatilmagan — DM o'tkazib yuborildi")
            return []

        self.ensure_login()
        messages: list[dict[str, Any]] = []
        fetch_limit = settings.INSTAGRAM_MESSAGE_FETCH_LIMIT
        check_limit = settings.INSTAGRAM_MESSAGE_LIMIT
        scanned = 0

        for conversation in self.zernio.list_conversations():
            conversation_id = conversation["id"]
            raw_messages = self.zernio.list_conversation_messages(conversation_id, limit=fetch_limit)

            incoming = [m for m in raw_messages if m.get("direction") == "incoming"]
            incoming.sort(key=lambda m: m.get("createdAt") or "", reverse=True)
            scanned += min(len(incoming), check_limit)

            for msg in incoming[:check_limit]:
                message_id = str(msg["id"])
                if not self._is_new_dm(message_id, msg.get("createdAt")):
                    continue

                text, image_url = self._extract_message_content(msg)
                if not text and not image_url:
                    continue

                messages.append(
                    {
                        "message_id": message_id,
                        "thread_id": str(conversation_id),
                        "user_id": str(msg.get("senderId", "")),
                        "text": text,
                        "image_url": image_url,
                        "has_image": bool(image_url),
                        "created_at": msg.get("createdAt"),
                    }
                )

        images = sum(1 for m in messages if m.get("has_image"))
        logger.info(
            "Instagram poll: %d ta tekshirildi, %d ta yangi DM (%d ta rasm)",
            scanned,
            len(messages),
            images,
        )
        return messages

    def fetch_new_comments(self, media_amount: int = 10) -> list[dict[str, Any]]:
        if not self.is_baseline_ready():
            return []

        self.ensure_login()
        comments: list[dict[str, Any]] = []
        account_info = self.zernio.get_account_info()
        owner_id = account_info.get("user_id", "")

        for post in self.zernio.list_posts_with_comments(limit=media_amount):
            post_id = post["id"]
            for comment in self.zernio.list_post_comments(post_id):
                comment_id = str(comment["id"])
                if not self._is_new_comment(comment_id):
                    continue

                sender = comment.get("from") or {}
                if str(sender.get("id", "")) == owner_id or sender.get("isOwner"):
                    continue
                text = (comment.get("message") or "").strip()
                if not text:
                    continue

                comments.append(
                    {
                        "comment_id": comment_id,
                        "media_id": str(post_id),
                        "user_id": str(sender.get("id", "")),
                        "username": sender.get("username") or sender.get("name") or "",
                        "text": text,
                    }
                )

        if comments:
            logger.info("Instagram poll: %d ta yangi izoh", len(comments))
        return comments

    def send_direct_reply(
        self,
        thread_id: str,
        text: str,
        *,
        image_url: str | None = None,
    ) -> None:
        self.ensure_login()
        self.zernio.send_direct_message(thread_id, text, image_url=image_url)
        logger.info("DM ga javob yuborildi: thread=%s image=%s", thread_id, bool(image_url))

    def send_private_comment_reply(
        self,
        media_id: str,
        comment_id: str,
        text: str,
        *,
        image_url: str | None = None,
    ) -> None:
        self.ensure_login()
        self.zernio.send_private_reply_to_comment(media_id, comment_id, text or " ")
        if image_url:
            logger.info("Private reply (rasm alohida DM): media=%s", media_id)

    def reply_to_comment(
        self,
        media_id: str,
        comment_id: str,
        text: str,
        username: str = "",
    ) -> None:
        self.ensure_login()
        self.zernio.reply_to_comment(media_id, comment_id, text, username)
        logger.info("Izohga javob yuborildi: media=%s comment=%s", media_id, comment_id)

    def get_account_info(self) -> dict[str, Any]:
        self.ensure_login()
        return self.zernio.get_account_info()
