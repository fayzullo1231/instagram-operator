import logging
from typing import Any

import httpx
from django.conf import settings
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class TezPOSClient:
    def __init__(self) -> None:
        self.base_url = settings.TEZPOS_API_URL.rstrip("/")
        self.server_name = settings.TEZPOS_SERVER_NAME
        self.api_token = settings.TEZPOS_API_TOKEN
        self.login = settings.TEZPOS_LOGIN
        self.password = settings.TEZPOS_PASSWORD
        self.timeout = httpx.Timeout(60.0, connect=15.0)

    @property
    def is_configured(self) -> bool:
        return bool(settings.TEZPOS_ENABLED and self.base_url and self.server_name)

    def _auth_headers(self) -> dict[str, str]:
        token = self.api_token or self._login()
        return {
            "Authorization": f"Token {token}",
            "X-Server-Name": self.server_name,
        }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def _login(self) -> str:
        if not self.login or not self.password:
            raise RuntimeError("TezPOS: token yoki login/parol kerak")

        url = f"{self.base_url}/api/auth/login/"
        logger.info("TezPOS API: login (%s)", self.server_name)

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
            raise RuntimeError("TezPOS login javobida token yo'q")
        return token

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def fetch_all_products(self) -> list[dict[str, Any]]:
        if not self.is_configured:
            return []

        url = f"{self.base_url}/api/external/products/"
        logger.info("TezPOS API: mahsulotlar yuklanmoqda (%s)", self.server_name)

        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(url, headers=self._auth_headers())
            response.raise_for_status()
            data = response.json()

        if not isinstance(data, list):
            logger.error("TezPOS API: kutilmagan javob formati")
            return []

        logger.info("TezPOS API: %d ta mahsulot yuklandi", len(data))
        return data

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
            "source": "tezpos",
            "category_hint": category_name,
            "keywords_hint": " ".join(keywords_parts),
        }
