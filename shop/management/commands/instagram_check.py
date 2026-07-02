from django.conf import settings
from django.core.management.base import BaseCommand

from shop.services.instagram_client import InstagramClient


class Command(BaseCommand):
    help = "Instagram (Zernio) holatini tekshirish"

    def handle(self, *args, **options):
        self.stdout.write("=== Instagram (Zernio) ===")
        self.stdout.write(f"INSTAGRAM_ENABLED: {settings.INSTAGRAM_ENABLED}")
        self.stdout.write(f"ZERNIO_API_KEY: {'bor' if settings.ZERNIO_API_KEY else 'yoq'}")
        self.stdout.write(f"ZERNIO_ACCOUNT_ID: {settings.ZERNIO_ACCOUNT_ID or 'avtomatik'}")

        client = InstagramClient()
        if not client.is_configured:
            self.stdout.write(self.style.ERROR(
                "\nZERNIO_API_KEY ni .env ga qo'shing.\n"
                "Instagram akkauntni ulang: https://zernio.com/dashboard"
            ))
            return

        try:
            info = client.get_account_info()
            self.stdout.write(self.style.SUCCESS(
                f"\nUlandi: @{info['username']} ({info['full_name']})"
            ))
            self.stdout.write(f"Account ID: {info.get('account_id')}")
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f"\nXato: {exc}"))
            self.stdout.write(
                "\nZernio dashboard da Instagram Business akkauntni ulang:\n"
                "https://zernio.com/dashboard"
            )
