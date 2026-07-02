import logging
from typing import Any

import httpx
from django.conf import settings
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class MDoKonClient:
    def __init__(self) -> None:
        self.api_url = settings.MDOKON_API_URL
        self.api_key = settings.MDOKON_API_KEY
        self.timeout = httpx.Timeout(30.0, connect=10.0)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def fetch_all_products(self) -> list[dict[str, Any]]:
        logger.info("MDoKon API: mahsulotlar yuklanmoqda")

        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                self.api_url,
                json={"apiKey": self.api_key},
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            data = response.json()

        if not isinstance(data, list):
            logger.error("MDoKon API: kutilmagan javob formati")
            return []

        logger.info("MDoKon API: jami %d ta mahsulot yuklandi", len(data))
        return data

    @staticmethod
    def parse_product(raw: dict[str, Any]) -> dict[str, Any]:
        return {
            "external_id": str(raw.get("productId", "")),
            "product_name": str(raw.get("productName", "")).strip(),
            "barcode": str(raw.get("productBarcode", "")) if raw.get("productBarcode") else None,
            "price": float(raw.get("salePrice", 0) or 0),
            "balance": float(raw.get("balance", 0) or 0),
            "source": "mdokon",
        }
