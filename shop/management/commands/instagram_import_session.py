from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Eski instagrapi sessiyasi — Zernio ishlatiladi, kerak emas"

    def handle(self, *args, **options):
        self.stdout.write(
            "Instagram endi Zernio orqali ishlaydi.\n"
            "Sessiya import kerak emas — faqat ZERNIO_API_KEY yetarli.\n"
            "Ko'rsatma: python manage.py instagram_check"
        )
