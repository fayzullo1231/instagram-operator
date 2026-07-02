from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Instagram Zernio orqali ulanadi — bu buyruq endi kerak emas"

    def handle(self, *args, **options):
        self.stdout.write(
            "Instagram endi Zernio.com orqali ishlaydi.\n\n"
            "1. https://zernio.com/dashboard ga kiring\n"
            "2. Instagram Business akkauntni ulang (OAuth)\n"
            "3. .env ga qo'shing:\n"
            "   ZERNIO_API_KEY=sk_...\n"
            "   ZERNIO_ACCOUNT_ID=...  (ixtiyoriy, avtomatik topiladi)\n\n"
            "4. Tekshirish: python manage.py instagram_check\n"
            "5. Server: .\\run.ps1"
        )
