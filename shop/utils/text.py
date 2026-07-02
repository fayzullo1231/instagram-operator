import re


def format_price(price: float | int) -> str:
    amount = int(round(float(price)))
    formatted = f"{amount:,}".replace(",", " ")
    return f"{formatted} so'm"


def normalize_search_text(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


STOP_WORDS = {
    "qancha", "nechpul", "nechchi", "necha", "bormi", "bor", "yoq",
    "narx", "narxi", "qanchadan", "dan", "ning", "ni", "ga", "da", "mi",
    "mavjud", "qayerda", "qanday", "iltimos", "salom", "assalomu", "alaykum",
    "aleykum", "alekum", "un", "uni", "haqida", "ayting", "yozing", "kerak",
    "olmoqchiman", "olaman", "sotib", "kg", "gr", "gramm", "kilogramm",
    "rahmat", "raxmat", "xayr", "hayr", "yaxshimisiz", "yaxshimisz",
    "hello", "hi", "hayrli", "xayrli", "kun", "kech", "tuningiz", "xayrli",
    "dostavka", "yetkazib", "manzil", "adres", "telefon", "ish vaqti",
    "ochiqmisiz", "price", "info", "malumot", "ma'lumot", "qiziq",
}

GREETING_PHRASES = {
    "assalomu alaykum",
    "salom alaykum",
    "salom alekum",
    "alaykum salom",
    "salom",
    "hayrli kun",
    "xayrli kun",
    "hayrli kech",
    "xayrli kech",
    "rahmat",
    "raxmat",
    "hello",
    "hi",
}


def extract_search_keywords(text: str) -> str:
    normalized = normalize_search_text(text)
    words = [w for w in normalized.split() if w not in STOP_WORDS and len(w) > 1]
    return " ".join(words)


def is_greeting_only(text: str) -> bool:
    normalized = normalize_search_text(text)
    if not normalized:
        return False
    if normalized in GREETING_PHRASES:
        return True
    return not extract_search_keywords(text) and len(normalized.split()) <= 5
