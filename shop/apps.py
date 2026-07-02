from django.apps import AppConfig


class ShopConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "shop"
    verbose_name = "Do'kon AI Operator"

    def ready(self) -> None:
        from shop.scheduler import start_scheduler

        start_scheduler()
