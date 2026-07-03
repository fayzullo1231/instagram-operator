from django.conf import settings
from django.core.management.base import BaseCommand

from shop.models import Product
from shop.services.kuloloptom_client import KulolOptomClient
from shop.services.mdokon_client import MDoKonClient
from shop.services.product_sync import ProductSyncService


class Command(BaseCommand):
    help = "Mahsulot API manbalarini tekshirish va sinxronizatsiya"

    def add_arguments(self, parser):
        parser.add_argument(
            "--sync",
            action="store_true",
            help="Tekshiruvdan keyin sinxronizatsiya qilish",
        )

    def handle(self, *args, **options):
        kulol = KulolOptomClient()
        mdokon = MDoKonClient()

        self.stdout.write("=== Sozlamalar ===")
        self.stdout.write(f"KULOLOPTOM_API_URL: {settings.KULOLOPTOM_API_URL}")
        self.stdout.write(f"KULOLOPTOM_SERVER_NAME: {settings.KULOLOPTOM_SERVER_NAME}")
        self.stdout.write(f"KULOLOPTOM_ENABLED: {settings.KULOLOPTOM_ENABLED}")
        self.stdout.write(
            f"KULOLOPTOM_API_TOKEN: {'bor' if kulol.api_token else 'YOQ'}"
        )
        self.stdout.write(
            f"KULOLOPTOM_LOGIN: {'bor' if kulol.login else 'yoq'}"
        )
        self.stdout.write(f"MDOKON_API_KEY: {'bor' if mdokon.is_configured else 'YOQ'}")

        self.stdout.write("")
        self.stdout.write("=== API holati ===")
        self.stdout.write(f"KulolOptom sozlangan: {kulol.is_configured}")

        if kulol.is_configured:
            try:
                items = kulol.fetch_all_products()
                self.stdout.write(self.style.SUCCESS(f"KulolOptom API: {len(items)} ta mahsulot"))
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f"KulolOptom API xato: {exc}"))
        else:
            self.stdout.write(
                self.style.WARNING(
                    "KulolOptom: TEZPOS_API_URL va KULOLOPTOM_SERVER_NAME kerak"
                )
            )

        if mdokon.is_configured:
            try:
                items = mdokon.fetch_all_products()
                self.stdout.write(self.style.SUCCESS(f"MDoKon API: {len(items)} ta mahsulot"))
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f"MDoKon API xato: {exc}"))
        else:
            self.stdout.write(self.style.WARNING("MDoKon: MDOKON_API_KEY kerak"))

        self._print_db_counts("Bazadagi mahsulotlar (sinxron oldin)")

        if options["sync"]:
            self.stdout.write("")
            self.stdout.write("Sinxronizatsiya boshlandi...")
            result = ProductSyncService().sync_all()
            self.stdout.write(str(result))
            self._print_db_counts("Bazadagi mahsulotlar (sinxron keyin)")

    def _print_db_counts(self, title: str) -> None:
        status = ProductSyncService().get_sync_status()
        self.stdout.write("")
        self.stdout.write(f"=== {title} ===")
        self.stdout.write(f"Linko: {status['linko_count']}")
        self.stdout.write(f"MDoKon: {status['mdokon_count']}")
        self.stdout.write(f"TezPOS: {status['tezpos_count']}")
        self.stdout.write(f"KulolOptom: {status['kuloloptom_count']}")
        self.stdout.write(f"Jami: {status['total_count']}")
        if status.get("last_errors"):
            self.stdout.write(f"Oxirgi xatolar: {status['last_errors']}")

        if status["kuloloptom_count"] == 0:
            db_any = Product.objects.filter(source="kuloloptom").exists()
            if db_any:
                self.stdout.write(
                    self.style.WARNING(
                        "Eslatma: kuloloptom manbasi bazada bor, lekin hisob 0 — "
                        "kod yangilanganini tekshiring (git pull)"
                    )
                )
