from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Admin panel uchun superuser yaratish yoki parolini yangilash"

    def add_arguments(self, parser):
        parser.add_argument("--username", default="admin")
        parser.add_argument("--email", default="admin@kuloloptom.uz")
        parser.add_argument("--password", default="")

    def handle(self, *args, **options):
        username = (options["username"] or "").strip()
        email = (options["email"] or "").strip()
        password = options["password"] or ""

        if not username:
            raise CommandError("Username bo'sh bo'lishi mumkin emas")
        if not password:
            raise CommandError("Parol kerak: --password yoki DJANGO_SUPERUSER_PASSWORD")

        user_model = get_user_model()
        user, created = user_model.objects.get_or_create(
            username=username,
            defaults={
                "email": email,
                "is_staff": True,
                "is_superuser": True,
            },
        )
        user.email = email
        user.is_staff = True
        user.is_superuser = True
        user.set_password(password)
        user.save()

        if created:
            self.stdout.write(self.style.SUCCESS(f"Superuser '{username}' yaratildi"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Superuser '{username}' paroli yangilandi"))
