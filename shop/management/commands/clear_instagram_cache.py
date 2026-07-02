from django.core.management.base import BaseCommand

from shop.models import ProcessedMessage


class Command(BaseCommand):
    help = "Instagram qayta ishlangan xabarlar ro'yxatini tozalash (test uchun)"

    def handle(self, *args, **options):
        count, _ = ProcessedMessage.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f"{count} ta yozuv o'chirildi"))
