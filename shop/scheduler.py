import logging
import os
import sys
import threading
import time

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from django.conf import settings

from shop.runtime import get_server_start_time

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None
_started = False

_MANAGEMENT_COMMANDS = frozenset({
        "shell", "migrate", "makemigrations", "test", "instagram_login",
        "instagram_import_session", "instagram_export_session", "instagram_check", "clear_instagram_cache",
    "collectstatic", "createsuperuser", "check", "showmigrations",
})


def sync_products_job() -> None:
    from shop.services.product_sync import ProductSyncService

    try:
        ProductSyncService().sync_all()
    except Exception as exc:
        logger.exception("Mahsulot sinxronizatsiya xatosi: %s", exc)


def instagram_poll_job() -> None:
    from shop.services.instagram_service import InstagramService

    try:
        result = InstagramService().poll_once()
        logger.info(
            "Instagram poll tugadi: dm=%s, izoh=%s, skipped=%s",
            result.get("dm_processed"),
            result.get("comment_processed"),
            result.get("skipped"),
        )
    except Exception as exc:
        logger.exception("Instagram polling xatosi: %s", exc)


def _init_instagram() -> None:
    try:
        from shop.services.instagram_client import InstagramClient

        client = InstagramClient()
        client.login()
        client.establish_baseline()
        info = client.get_account_info()
        logger.info("Instagram ulandi: @%s (Zernio) — yangi xabarlarni kutmoqda", info["username"])
    except Exception as exc:
        logger.warning("Instagram: %s", exc)


def _instagram_status_label() -> str:
    if not settings.INSTAGRAM_ENABLED:
        return "o'chiq"

    from shop.services.instagram_client import InstagramClient

    client = InstagramClient()
    if not client.is_configured:
        return "ZERNIO_API_KEY yo'q"
    try:
        info = client.get_account_info()
        return f"@{info['username']}"
    except Exception:
        return "Zernio — akkaunt ulang"


def _product_count() -> int:
    from shop.models import Product

    return Product.objects.count()


def _should_skip_scheduler() -> bool:
    if os.environ.get("SCHEDULER_ENABLED", "").lower() == "true":
        return False

    argv = sys.argv
    if not argv:
        return True

    prog = os.path.basename(argv[0]).lower()
    if "gunicorn" in prog or any("gunicorn" in arg.lower() for arg in argv):
        return False

    command = argv[1] if len(argv) >= 2 else ""
    if command in _MANAGEMENT_COMMANDS or "pytest" in " ".join(argv):
        return True

    if command != "runserver":
        return True

    if "--noreload" in argv:
        return False

    return os.environ.get("RUN_MAIN") != "true"


def _startup_tasks(instagram_ready: bool) -> None:
    """DB va fon ishlar — ready() dan keyin."""
    time.sleep(0.5)
    product_count = _product_count()

    logger.info(
        "Tayyor | mahsulotlar: %d | sync: %d min | instagram: %s",
        product_count,
        settings.SYNC_INTERVAL_MINUTES,
        _instagram_status_label(),
    )

    if instagram_ready:
        _init_instagram()

    if settings.SYNC_ON_STARTUP or product_count == 0:
        delay = settings.SYNC_STARTUP_DELAY_SECONDS if settings.SYNC_ON_STARTUP else 0
        if delay > 0:
            time.sleep(delay)
        sync_products_job()


def start_scheduler() -> None:
    global _scheduler, _started

    if _started or _should_skip_scheduler():
        return

    _scheduler = BackgroundScheduler()
    _scheduler.add_job(
        sync_products_job,
        trigger=IntervalTrigger(minutes=settings.SYNC_INTERVAL_MINUTES),
        id="product_sync",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    instagram_ready = False
    if settings.INSTAGRAM_ENABLED:
        from shop.services.instagram_client import InstagramClient

        ig = InstagramClient()
        if ig.can_auto_connect():
            instagram_ready = True
            _scheduler.add_job(
                instagram_poll_job,
                trigger=IntervalTrigger(seconds=settings.INSTAGRAM_POLL_INTERVAL_SECONDS),
                id="instagram_poll",
                replace_existing=True,
                max_instances=1,
                coalesce=True,
            )

    _scheduler.start()
    _started = True

    threading.Thread(
        target=_startup_tasks,
        args=(instagram_ready,),
        daemon=True,
        name="startup-tasks",
    ).start()


def stop_scheduler() -> None:
    global _scheduler, _started
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
    _scheduler = None
    _started = False
