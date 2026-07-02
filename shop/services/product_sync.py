import logging

from django.db.models import Max

from shop.models import Product
from shop.services.catalog_config import infer_product_metadata
from shop.services.linko_client import LinkoClient
from shop.services.mdokon_client import MDoKonClient
from shop.services.tezpos_client import TezPOSClient

logger = logging.getLogger(__name__)


class ProductSyncService:
    def __init__(self) -> None:
        self.linko_client = LinkoClient()
        self.mdokon_client = MDoKonClient()
        self.tezpos_client = TezPOSClient()

    def sync_all(self) -> dict[str, int]:
        logger.info("Sinxronizatsiya boshlandi...")

        linko_raw = self.linko_client.fetch_all_products()
        mdokon_raw = self.mdokon_client.fetch_all_products()
        tezpos_raw = self.tezpos_client.fetch_all_products() if self.tezpos_client.is_configured else []

        linko_products = [
            self.linko_client.parse_product(item)
            for item in linko_raw
            if item.get("name") and not item.get("is_delete")
        ]
        mdokon_products = [
            self.mdokon_client.parse_product(item)
            for item in mdokon_raw
            if item.get("productName")
        ]
        tezpos_products = [
            self.tezpos_client.parse_product(item)
            for item in tezpos_raw
            if item.get("name") and item.get("is_active", True)
        ]

        linko_count = self._upsert_products(linko_products)
        mdokon_count = self._upsert_products(mdokon_products)
        tezpos_count = self._upsert_products(tezpos_products)

        total = linko_count + mdokon_count + tezpos_count
        logger.info(
            "Sinxronizatsiya tugadi: linko=%d, mdokon=%d, tezpos=%d, jami=%d",
            linko_count,
            mdokon_count,
            tezpos_count,
            total,
        )
        return {
            "linko_count": linko_count,
            "mdokon_count": mdokon_count,
            "tezpos_count": tezpos_count,
            "total_count": total,
        }

    def _upsert_products(self, products: list[dict]) -> int:
        objects: list[Product] = []
        for item in products:
            if not item.get("external_id") or not item.get("product_name"):
                continue
            meta = infer_product_metadata(item["product_name"])
            category = item.get("category_hint") or meta["category"]
            keywords = meta["keywords"]
            extra = str(item.get("keywords_hint") or "").strip()
            if extra:
                keywords = f"{keywords} {extra}".strip() if keywords else extra
            objects.append(
                Product(
                    source=item["source"],
                    external_id=item["external_id"],
                    product_name=item["product_name"],
                    barcode=item.get("barcode"),
                    price=item.get("price", 0.0),
                    balance=item.get("balance", 0.0),
                    category=category,
                    keywords=keywords,
                )
            )

        if not objects:
            return 0

        batch_size = 500
        for i in range(0, len(objects), batch_size):
            Product.objects.bulk_create(
                objects[i : i + batch_size],
                update_conflicts=True,
                unique_fields=["source", "external_id"],
                update_fields=["product_name", "barcode", "price", "balance", "category", "keywords"],
            )
        return len(objects)

    def get_sync_status(self) -> dict:
        linko_count = Product.objects.filter(source="linko").count()
        mdokon_count = Product.objects.filter(source="mdokon").count()
        tezpos_count = Product.objects.filter(source="tezpos").count()
        last_sync = Product.objects.aggregate(last=Max("updated_at"))["last"]

        return {
            "linko_count": linko_count,
            "mdokon_count": mdokon_count,
            "tezpos_count": tezpos_count,
            "total_count": linko_count + mdokon_count + tezpos_count,
            "last_sync": last_sync.isoformat() if last_sync else None,
        }
