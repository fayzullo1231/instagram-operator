from django.core.management.base import BaseCommand

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

        self.stdout.write("=== API holati ===")
        self.stdout.write(f"KulolOptom sozlangan: {kulol.is_configured}")
        self.stdout.write(f"MDoKon sozlangan: {mdokon.is_configured}")

        if kulol.is_configured:
            try:
                items = kulol.fetch_all_products()
                self.stdout.write(self.style.SUCCESS(f"KulolOptom: {len(items)} ta mahsulot"))
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f"KulolOptom xato: {exc}"))
        else:
            self.stdout.write(
                self.style.WARNING(
                    "KulolOptom: KULOLOPTOM_LOGIN/PASSWORD yoki TOKEN kerak (.env)"
                )
            )

        if mdokon.is_configured:
            try:
                items = mdokon.fetch_all_products()
                self.stdout.write(self.style.SUCCESS(f"MDoKon: {len(items)} ta mahsulot"))
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f"MDoKon xato: {exc}"))
        else:
            self.stdout.write(self.style.WARNING("MDoKon: MDOKON_API_KEY kerak (.env)"))

        status = ProductSyncService().get_sync_status()
        self.stdout.write("")
        self.stdout.write("=== Bazadagi mahsulotlar ===")
        self.stdout.write(f"Linko: {status['linko_count']}")
        self.stdout.write(f"MDoKon: {status['mdokon_count']}")
        self.stdout.write(f"TezPOS: {status['tezpos_count']}")
        self.stdout.write(f"KulolOptom: {status['kuloloptom_count']}")
        self.stdout.write(f"Jami: {status['total_count']}")

        if options["sync"]:
            self.stdout.write("")
            self.stdout.write("Sinxronizatsiya boshlandi...")
            result = ProductSyncService().sync_all()
            self.stdout.write(str(result))
