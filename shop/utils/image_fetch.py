import base64
import logging

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)

_DOWNLOAD_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
    "Referer": "https://www.instagram.com/",
}


def fetch_image_as_data_url(url: str, *, timeout: float = 30.0) -> str | None:
    """Instagram CDN rasmini yuklab, OpenAI uchun base64 data URL qaytaradi."""
    headers = dict(_DOWNLOAD_HEADERS)
    if settings.ZERNIO_API_KEY and "fbsbx" in url:
        headers["Authorization"] = f"Bearer {settings.ZERNIO_API_KEY}"

    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()

            content_type = (response.headers.get("content-type") or "image/jpeg").split(";")[0].strip()
            if not content_type.startswith("image/"):
                content_type = "image/jpeg"

            if len(response.content) < 100:
                logger.warning("Rasm juda kichik yoki bo'sh: %d bayt", len(response.content))
                return None

            encoded = base64.standard_b64encode(response.content).decode("ascii")
            logger.info("Rasm yuklandi: %d bayt", len(response.content))
            return f"data:{content_type};base64,{encoded}"
    except Exception as exc:
        logger.warning("Rasm yuklab olinmadi: %s", exc)
        return None
