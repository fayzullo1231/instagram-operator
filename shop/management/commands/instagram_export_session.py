from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Eski instagrapi sessiyasi — Zernio ishlatiladi, kerak emas"

    def handle(self, *args, **options):
        self.stdout.write(
            "Instagram endi Zernio orqali ishlaydi.\n"
            "Sessiya eksport kerak emas."
        )
