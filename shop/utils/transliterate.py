"""Kirill → lotin va mahsulot nomlari sinonimlari."""

from __future__ import annotations

import re

from shop.utils.text import normalize_search_text

CYRILLIC_TO_LATIN: dict[str, str] = {
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "g",
    "д": "d",
    "е": "e",
    "ё": "e",
    "ж": "zh",
    "з": "z",
    "и": "i",
    "й": "y",
    "к": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ф": "f",
    "х": "h",
    "ц": "ts",
    "ч": "ch",
    "ш": "sh",
    "щ": "sch",
    "ъ": "",
    "ы": "y",
    "ь": "",
    "э": "e",
    "ю": "yu",
    "я": "ya",
}

BRAND_ALIASES: dict[str, str] = {
    "marimoloko": "mari",
    "mari moloko": "mari",
    "maru moloko": "mari",
}

TOKEN_ALIASES: dict[str, str] = {
    "moloko": "malako",
    "sgushchenka": "malako",
    "sguschenka": "malako",
    "sgushchennoe": "malako",
    "sgushchenno": "malako",
    "sgushenka": "malako",
    "sgushennoe": "malako",
    "sghushchenka": "malako",
    "sghushchennoe": "malako",
    "condensed": "malako",
    "sgushchennoye": "malako",
    "bugdoy": "uni",
    "bugdoyuni": "uni",
    "bugdoynuni": "uni",
    "bugdoyn": "uni",
    "flour": "uni",
    "un": "uni",
}

FLOUR_KEYWORDS = ("uni", "un", "bugdoy", "bugdoyn", "flour", "turon", "altyn", "kanash", "samo", "samokat")

LIQUID_KEYWORDS = (
    "yog",
    "yogi",
    "oil",
    "zaytun",
    "olive",
    "sunflower",
    "leslyak",
    "zateya",
    "litr",
    "litre",
    "malako",
    "moloko",
)


def _normalize_volume_string(value: str) -> str:
    cleaned = value.replace(",", ".").strip()
    if not cleaned:
        return ""
    try:
        number = float(cleaned)
        if number.is_integer():
            return str(int(number))
        return str(number).rstrip("0").rstrip(".")
    except ValueError:
        return cleaned


def is_liquid_context(*parts: str) -> bool:
    combined = latinize(" ".join(str(part) for part in parts if part))
    return any(keyword in combined for keyword in LIQUID_KEYWORDS) or bool(
        re.search(r"\d+(?:[.,]\d+)?\s*(?:l|litr|litre|lt|ml|л)\b", combined)
    )

GRADE_PATTERNS: list[tuple[str, list[str]]] = [
    ("vs", ["v s", "v/s", "vs", "vysch", "vyssh", "vysshy", "vyshey", "в/с", "высший", "высш"]),
    ("1s", ["1 s", "1/s", "1s", "1 sort", "1/sort", "1/с", "перв"]),
]


def latinize(text: str) -> str:
    if not text:
        return ""
    converted: list[str] = []
    for char in text.lower():
        if char in CYRILLIC_TO_LATIN:
            converted.append(CYRILLIC_TO_LATIN[char])
        else:
            converted.append(char)
    return normalize_search_text("".join(converted))


def canonical_brand(text: str) -> str:
    normalized = latinize(text).replace(" ", "")
    for alias, brand in sorted(BRAND_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
        if alias.replace(" ", "") in normalized:
            return brand
    words = latinize(text).split()
    return words[0] if words else ""


def canonical_tokens(text: str) -> list[str]:
    tokens = latinize(text).split()
    result: list[str] = []
    for token in tokens:
        mapped = TOKEN_ALIASES.get(token, token)
        if mapped and mapped not in result:
            result.append(mapped)
    return result


def build_catalog_search_text(*parts: str) -> str:
    chunks: list[str] = []
    for part in parts:
        if not part:
            continue
        latin = latinize(part)
        if not latin:
            continue
        brand = canonical_brand(part)
        if brand:
            chunks.append(brand)
        chunks.extend(canonical_tokens(part))
        if latin not in chunks:
            chunks.append(latin)
    unique: list[str] = []
    seen: set[str] = set()
    for chunk in chunks:
        key = normalize_search_text(chunk)
        if key and key not in seen:
            seen.add(key)
            unique.append(key)
    return " ".join(unique)


def extract_volume_digits(text: str) -> str:
    return re.sub(r"[^\d]", "", latinize(text))


def detect_product_grade(text: str) -> str:
    normalized = latinize(text)
    if not normalized:
        return ""
    for grade, patterns in GRADE_PATTERNS:
        for pattern in patterns:
            if pattern in normalized or pattern in text.lower():
                return grade
    return ""


def is_flour_context(*parts: str) -> bool:
    combined = latinize(" ".join(part for part in parts if part))
    return any(keyword in combined for keyword in FLOUR_KEYWORDS)


def normalize_product_weight(value: object, *context_parts: str) -> str:
    """Katalog qidiruvi uchun hajm/og'irlik raqami."""
    raw_context = " ".join(str(part) for part in context_parts if part).lower()
    context = latinize(raw_context)
    raw = str(value or "").strip()
    if re.search(r"[.,]", raw):
        parsed = _normalize_volume_string(raw)
        if parsed:
            return parsed

    for source in (raw_context, raw.lower(), context):
        decimal_liter = re.search(r"(\d+[.,]\d+)\s*(?:l|litr|litre|lt|л)\b", source, flags=re.IGNORECASE)
        if not decimal_liter:
            decimal_liter = re.search(r"(\d+[.,]\d+)(?:l|litr|litre|lt|л)\b", source, flags=re.IGNORECASE)
        if decimal_liter:
            return _normalize_volume_string(decimal_liter.group(1))

        liter = re.search(r"(\d+)\s*(?:l|litr|litre|lt|л)\b", source, flags=re.IGNORECASE)
        if not liter:
            liter = re.search(r"(\d+)(?:l|litr|litre|lt|л)\b", source, flags=re.IGNORECASE)
        if liter:
            return _normalize_volume_string(liter.group(1))

    kg_match = re.search(r"(\d+)\s*(?:kg|kg\b|кг)", context, flags=re.IGNORECASE)
    if not kg_match:
        kg_match = re.search(r"(\d+)\s*(?:kg|кг)", raw, flags=re.IGNORECASE)
    if kg_match:
        return kg_match.group(1)

    digits = extract_volume_digits(raw)
    if not digits:
        return ""

    amount = int(digits)
    if is_flour_context(context, raw) and amount >= 1000 and amount % 1000 == 0:
        return str(amount // 1000)

    if is_flour_context(context, raw) and amount in {1, 2, 3, 5, 10, 25, 50}:
        return str(amount)

    if is_liquid_context(context, raw):
        if amount % 1000 == 0 and amount >= 1000:
            return str(amount // 1000)
        if amount % 100 == 0 and amount in {500, 1800}:
            return _normalize_volume_string(str(amount / 1000))

    return digits


def product_name_latin(name: str) -> str:
    return latinize(name)


def extract_primary_weight(name: str) -> str:
    raw = (name or "").lower()

    decimal_liter = re.search(r"(\d+[.,]\d+)\s*(?:l|litr|litre|lt|л)\b", raw, flags=re.IGNORECASE)
    if not decimal_liter:
        decimal_liter = re.search(r"(\d+[.,]\d+)(?:l|litr|litre|lt|л)\b", raw, flags=re.IGNORECASE)
    if decimal_liter:
        return _normalize_volume_string(decimal_liter.group(1))

    liter = re.search(r"(\d+)\s*(?:l|litr|litre|lt|л)\b", raw, flags=re.IGNORECASE)
    if not liter:
        liter = re.search(r"(\d+)(?:l|litr|litre|lt|л)\b", raw, flags=re.IGNORECASE)
    if liter:
        return _normalize_volume_string(liter.group(1))

    haystack = product_name_latin(name)
    if not haystack:
        return ""

    kg = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:kg|kg)\b", haystack)
    if kg:
        return _normalize_volume_string(kg.group(1))

    metric = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:ml|g|gr)\b", haystack)
    if metric:
        return _normalize_volume_string(metric.group(1))

    return ""


def weights_match(expected: str, product_name: str) -> bool:
    if not expected:
        return True
    return _normalize_volume_string(expected) == extract_primary_weight(product_name)


def product_matches_grade(product_name: str, grade: str) -> bool:
    if not grade:
        return True
    haystack = latinize(product_name)
    if grade == "vs":
        return "v s" in haystack or "vs" in haystack.split()
    if grade == "1s":
        return "1 s" in haystack or "1/s" in haystack.replace(" ", "")
    return True
