import json
import logging

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from shop.services.ai_operator import AIOperatorService
from shop.services.instagram_service import InstagramService
from shop.services.product_sync import ProductSyncService

logger = logging.getLogger(__name__)


@require_GET
def health(request):
    return JsonResponse({"status": "ok"})


@require_GET
def ready(request):
    return JsonResponse({"status": "ready"})


@csrf_exempt
@require_POST
def chat(request):
    try:
        body = json.loads(request.body.decode("utf-8"))
        message = body.get("message", "").strip()
        if not message:
            return JsonResponse({"error": "message maydoni kerak"}, status=400)

        response = AIOperatorService().process_message(message)
        return JsonResponse({"reply": response.reply, "matches": response.matches})
    except json.JSONDecodeError:
        return JsonResponse({"error": "Noto'g'ri JSON"}, status=400)
    except Exception as exc:
        logger.exception("Chat xatosi: %s", exc)
        return JsonResponse({"error": "Xabar qayta ishlashda xato"}, status=500)


@csrf_exempt
@require_POST
def sync_products(request):
    try:
        result = ProductSyncService().sync_all()
        return JsonResponse({"status": "success", **result})
    except Exception as exc:
        logger.exception("Sinxronizatsiya xatosi: %s", exc)
        return JsonResponse({"error": "Sinxronizatsiya xatosi"}, status=500)


@require_GET
def sync_status(request):
    return JsonResponse(ProductSyncService().get_sync_status())


@require_GET
def instagram_status(request):
    return JsonResponse(InstagramService().get_status())


@csrf_exempt
@require_POST
def instagram_poll(request):
    try:
        result = InstagramService().poll_once()
        return JsonResponse({"status": "success", **result})
    except Exception as exc:
        logger.exception("Instagram poll xatosi: %s", exc)
        return JsonResponse({"error": "Instagram polling xatosi"}, status=500)
