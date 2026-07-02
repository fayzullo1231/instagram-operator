import logging
from typing import Any

import httpx
from django.conf import settings
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class LinkoClient:
    def __init__(self) -> None:
        self.base_url = settings.LINKO_API_URL.rstrip("/") + "/"
        self.token = settings.LINKO_API_TOKEN
        self.timeout = httpx.Timeout(30.0, connect=10.0)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def fetch_all_products(self) -> list[dict[str, Any]]:
        products: list[dict[str, Any]] = []
        page = 1
        logger.info("Linko API: yuklanmoqda...")

        with httpx.Client(timeout=self.timeout) as client:
            while True:
                url = f"{self.base_url}?page={page}"
                logger.debug("Linko API: page=%d", page)

                response = client.get(
                    url,
                    headers={"Authorization": f"Token {self.token}"},
                )
                response.raise_for_status()
                data = response.json()

                results = data.get("results", [])
                products.extend(results)
                logger.debug("Linko page=%d: %d ta mahsulot", page, len(results))

                if not data.get("next"):
                    break
                page += 1

        logger.info("Linko API: %d ta mahsulot (%d sahifa)", len(products), page)
        return products

    @staticmethod
    def parse_product(raw: dict[str, Any]) -> dict[str, Any]:
        price = 0.0
        prices = raw.get("prices") or []
        if prices:
            try:
                price = float(prices[0].get("cash_price", 0))
            except (TypeError, ValueError):
                price = 0.0

        barcode = (
            raw.get("vendor_code")
            or raw.get("stock_number")
            or raw.get("plu")
            or raw.get("ikpu")
        )

        return {
            "external_id": str(raw.get("uuid", "")),
            "product_name": str(raw.get("name", "")).strip(),
            "barcode": str(barcode) if barcode else None,
            "price": price,
            "balance": 0.0,
            "source": "linko",
        }
