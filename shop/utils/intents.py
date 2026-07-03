import re
from enum import Enum

from shop.utils.text import extract_search_keywords, normalize_search_text


class Intent(str, Enum):
    GREETING = "greeting"
    THANKS = "thanks"
    ADDRESS = "address"
    PHONE = "phone"
    HOURS = "hours"
    DELIVERY = "delivery"
    PRICE = "price"
    AVAILABILITY = "availability"
    COMMENT_LEAD = "comment_lead"
    PRODUCT = "product"
    GENERAL = "general"


_GREETING = {
    "salom", "assalomu alaykum", "alaykum salom", "salom alaykum",
    "hello", "hi", "hayrli kun", "xayrli kun",
}
_THANKS = {"rahmat", "raxmat", "thanks", "thank you", "tashakkur"}
_ADDRESS = {"qayerdasiz", "manzil", "lokatsiya", "adres", "address", "qayerda"}
_PHONE = {"telefon", "tel", "raqam", "aloqa", "phone", "kontakt"}
_HOURS = {"qachongacha ishlaysiz", "ish vaqti", "ochiqmisiz", "ishlayaptimi", "vaqt"}
_DELIVERY = {"yetkazib berish", "dostavka", "delivery", "yetkazib"}
_PRICE = {"narx", "qancha", "price", "nechi pul", "nechpul", "necha", "narxi", "qanchadan"}
_AVAILABILITY = {"bormi", "bor", "mavjud", "qolgan", "qoldimi", "borimi"}
_COMMENT_LEAD = {"+", "info", "malumot", "ma'lumot", "kerak", "qiziq"}


def detect_intent(message: str) -> Intent:
    normalized = normalize_search_text(message)
    if not normalized:
        return Intent.GENERAL

    if normalized in _GREETING:
        return Intent.GREETING

    words = set(normalized.split())

    if words <= _THANKS or normalized in _THANKS:
        return Intent.THANKS

    if any(kw in normalized for kw in _ADDRESS):
        return Intent.ADDRESS

    if any(kw in normalized for kw in _PHONE):
        return Intent.PHONE

    if any(kw in normalized for kw in _HOURS):
        return Intent.HOURS

    if any(kw in normalized for kw in _DELIVERY):
        return Intent.DELIVERY

    if normalized.strip("+") in _COMMENT_LEAD or words & _COMMENT_LEAD:
        return Intent.COMMENT_LEAD

    asks_price = bool(words & _PRICE) or any(kw in normalized for kw in _PRICE)
    asks_avail = bool(words & _AVAILABILITY)

    if asks_price and not asks_avail:
        return Intent.PRICE
    if asks_avail:
        return Intent.AVAILABILITY

    from shop.utils.text import extract_search_keywords

    if extract_search_keywords(message):
        return Intent.PRODUCT

    return Intent.GENERAL
