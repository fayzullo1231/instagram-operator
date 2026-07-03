import logging
from typing import Any
from urllib.parse import urlencode

import httpx
from django.conf import settings
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class KulolOptomClient:
    """TezPOS tenant API: /{server_name}/product/?all=true"""

    def __init__(self) -> None:
        self.base_url = settings.TEZPOS_API_URL.rstrip("/")
        self.server_name = settings.KULOLOPTOM_SERVER_NAME
        self.api_token = (settings.KULOLOPTOM_API_TOKEN or "").strip()
        self.login = (settings.KULOLOPTOM_LOGIN or "").strip()
        self.password = (settings.KULOLOPTOM_PASSWORD or "").strip()
        self.timeout = httpx.Timeout(60.0, connect=15.0)
        self._cached_token = ""

    @property
    def is_configured(self) -> bool:
        return bool(settings.KULOLOPTOM_ENABLED and self.base_url and self.server_name)

    @property
    def has_auth_credentials(self) -> bool:
        return bool(self.api_token or (self.login and self.password))

    def _product_url(self) -> str:
        query = urlencode({"all": "true"})
        return f"{self.base_url}/{self.server_name}/product/?{query}"

    def _auth_headers(self) -> dict[str, str]:
        token = self.api_token or self._cached_token or self._login()
        self._cached_token = token
        return {
            "Authorization": f"Token {token}",
            "X-Server-Name": self.server_name,
        }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def _login(self) -> str:
        if not self.login or not self.password:
            raise RuntimeError("KulolOptom: token yoki login/parol kerak")

        url = f"{self.base_url}/api/auth/login/"
        logger.info("KulolOptom API: login (%s)", self.server_name)

        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                url,
                json={
                    "server_name": self.server_name,
                    "login": self.login,
                    "password": self.password,
                },
            )
            response.raise_for_status()
            data = response.json()

        token = str(data.get("token") or "").strip()
        if not token:
            raise RuntimeError("KulolOptom login javobida token yo'q")
        return token

    @staticmethod
    def _parse_response(data: Any) -> list[dict[str, Any]]:
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in ("results", "data", "items", "products"):
                items = data.get(key)
                if isinstance(items, list):
                    return items
        logger.error("KulolOptom API: kutilmagan javob formati")
        return []

    def _get_products(self, *, use_auth: bool) -> list[dict[str, Any]]:
        url = self._product_url()
        headers = self._auth_headers() if use_auth else None
        mode = "auth" if use_auth else "public"

        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(url, headers=headers)

        if response.status_code == 401 and not use_auth:
            logger.info("KulolOptom API: tokensiz kirish rad etildi (%s)", self.server_name)
            return []

        response.raise_for_status()
        products = self._parse_response(response.json())
        logger.info(
            "KulolOptom API (%s): %d ta mahsulot yuklandi",
            mode,
            len(products),
        )
        return products

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def fetch_all_products(self) -> list[dict[str, Any]]:
        if not self.is_configured:
            return []

        logger.info("KulolOptom API: mahsulotlar yuklanmoqda (%s)", self.server_name)

        products = self._get_products(use_auth=False)
        if products:
            return products

        if self.has_auth_credentials:
            logger.info("KulolOptom API: token/login bilan qayta urinilmoqda")
            return self._get_products(use_auth=True)

        raise RuntimeError(
            "KulolOptom mahsulotlari yuklanmadi. "
            "Serverda TEZPOS_API_URL=http://127.0.0.1:8000 bo'lishi kerak "
            "yoki KULOLOPTOM_LOGIN/PASSWORD qo'shing."
        )

    @staticmethod
    def parse_product(raw: dict[str, Any]) -> dict[str, Any]:
        price = 0.0
        try:
            price = float(raw.get("price", 0) or 0)
        except (TypeError, ValueError):
            price = 0.0

        balance = 0.0
        try:
            balance = float(raw.get("quantity", 0) or 0)
        except (TypeError, ValueError):
            balance = 0.0

        barcode = raw.get("barcode")
        if not barcode:
            barcodes = raw.get("barcodes") or []
            barcode = barcodes[0] if barcodes else None

        category_name = str(raw.get("category_name") or "").strip()
        brand_name = str(raw.get("brand_name") or "").strip()
        keywords_parts = [part for part in (category_name, brand_name) if part]

        return {
            "external_id": str(raw.get("id", "")),
            "product_name": str(raw.get("name", "")).strip(),
            "barcode": str(barcode) if barcode else None,
            "price": price,
            "balance": balance,
            "source": "kuloloptom",
            "category_hint": category_name,
            "keywords_hint": " ".join(keywords_parts),
        }
