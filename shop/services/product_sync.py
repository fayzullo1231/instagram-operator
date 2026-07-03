import logging
from typing import Any, Callable

from shop.models import Product
from shop.services.catalog_config import infer_product_metadata
from shop.services.kuloloptom_client import KulolOptomClient
from shop.services.linko_client import LinkoClient
from shop.services.mdokon_client import MDoKonClient
from shop.services.tezpos_client import TezPOSClient

logger = logging.getLogger(__name__)

_last_sync_report: dict[str, Any] = {}


class ProductSyncService:
    def __init__(self) -> None:
        self.linko_client = LinkoClient()
        self.mdokon_client = MDoKonClient()
        self.tezpos_client = TezPOSClient()
        self.kuloloptom_client = KulolOptomClient()

    def sync_all(self) -> dict[str, int | dict[str, str]]:
        global _last_sync_report
        logger.info("Sinxronizatsiya boshlandi...")
        errors: dict[str, str] = {}

        linko_count, linko_error = self._sync_source(
            "linko",
            lambda: self.linko_client.fetch_all_products(),
            lambda item: self.linko_client.parse_product(item),
            lambda item: bool(item.get("name") and not item.get("is_delete")),
        )
        if linko_error:
            errors["linko"] = linko_error

        mdokon_count, mdokon_error = self._sync_source(
            "mdokon",
            lambda: self.mdokon_client.fetch_all_products(),
            lambda item: self.mdokon_client.parse_product(item),
            lambda item: bool(item.get("productName")),
            skip_if=lambda: not self.mdokon_client.is_configured,
            skip_reason="MDOKON_API_KEY sozlanmagan",
        )
        if mdokon_error:
            errors["mdokon"] = mdokon_error

        tezpos_count, tezpos_error = self._sync_source(
            "tezpos",
            lambda: self.tezpos_client.fetch_all_products(),
            lambda item: self.tezpos_client.parse_product(item),
            lambda item: bool(item.get("name") and item.get("is_active", True)),
            skip_if=lambda: not self.tezpos_client.is_configured,
            skip_reason="TezPOS sozlanmagan",
        )
        if tezpos_error:
            errors["tezpos"] = tezpos_error

        kuloloptom_count, kuloloptom_error = self._sync_source(
            "kuloloptom",
            lambda: self.kuloloptom_client.fetch_all_products(),
            lambda item: self.kuloloptom_client.parse_product(item),
            lambda item: bool(item.get("name") and item.get("is_active", True)),
            skip_if=lambda: not self.kuloloptom_client.is_configured,
            skip_reason="KulolOptom o'chirilgan yoki TEZPOS_API_URL yo'q",
        )
        if kuloloptom_error:
            errors["kuloloptom"] = kuloloptom_error

        total = linko_count + mdokon_count + tezpos_count + kuloloptom_count
        logger.info(
            "Sinxronizatsiya tugadi: linko=%d, mdokon=%d, tezpos=%d, kuloloptom=%d, jami=%d, xatolar=%d",
            linko_count,
            mdokon_count,
            tezpos_count,
            kuloloptom_count,
            total,
            len(errors),
        )
        result = {
            "linko_count": linko_count,
            "mdokon_count": mdokon_count,
            "tezpos_count": tezpos_count,
            "kuloloptom_count": kuloloptom_count,
            "total_count": total,
            "errors": errors,
        }
        _last_sync_report = result
        return result

    def _sync_source(
        self,
        source: str,
        fetch_fn: Callable[[], list[dict[str, Any]]],
        parse_fn: Callable[[dict[str, Any]], dict[str, Any]],
        include_fn: Callable[[dict[str, Any]], bool],
        *,
        skip_if: Callable[[], bool] | None = None,
        skip_reason: str = "",
    ) -> tuple[int, str]:
        if skip_if and skip_if():
            logger.warning("%s sinxronizatsiyasi o'tkazib yuborildi: %s", source, skip_reason)
            return 0, ""

        try:
            raw_items = fetch_fn()
            products = [parse_fn(item) for item in raw_items if include_fn(item)]
            count = self._upsert_products(products)
            logger.info("%s sinxronizatsiyasi: %d ta mahsulot", source, count)
            return count, ""
        except Exception as exc:
            message = str(exc).strip() or exc.__class__.__name__
            logger.exception("%s sinxronizatsiya xatosi: %s", source, exc)
            return 0, message

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
        from django.db.models import Max

        linko_count = Product.objects.filter(source="linko").count()
        mdokon_count = Product.objects.filter(source="mdokon").count()
        tezpos_count = Product.objects.filter(source="tezpos").count()
        kuloloptom_count = Product.objects.filter(source="kuloloptom").count()
        last_sync = Product.objects.aggregate(last=Max("updated_at"))["last"]

        return {
            "linko_count": linko_count,
            "mdokon_count": mdokon_count,
            "tezpos_count": tezpos_count,
            "kuloloptom_count": kuloloptom_count,
            "total_count": linko_count + mdokon_count + tezpos_count + kuloloptom_count,
            "last_sync": last_sync.isoformat() if last_sync else None,
            "kuloloptom_configured": self.kuloloptom_client.is_configured,
            "kuloloptom_has_auth": self.kuloloptom_client.has_auth_credentials,
            "mdokon_configured": self.mdokon_client.is_configured,
            "tezpos_configured": self.tezpos_client.is_configured,
            "last_errors": dict(_last_sync_report.get("errors") or {}),
        }