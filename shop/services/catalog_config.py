"""Mahsulot kategoriyalari, brendlar va sinonimlar."""

CATEGORY_SYNONYMS: dict[str, list[str]] = {
    "tushonka": ["tushonka", "tushtonka", "gosht konservasi", "konserva", "konservalar"],
    "zaytun yog'i": ["zaytun yog'i", "zaytun yogi", "olivka yog'i", "olivka yogi", "olive oil", "zaytun"],
    "makaron": ["makaron", "spagetti", "pasta", "makaronlar"],
}

BRAND_CATEGORIES: dict[str, str] = {
    "ansor": "tushonka",
    "poyqadam": "tushonka",
    "halol": "tushonka",
}


def canonical_category(term: str) -> str | None:
    normalized = term.lower().strip()
    for category, synonyms in CATEGORY_SYNONYMS.items():
        if normalized == category or normalized in synonyms:
            return category
    return None


def expand_search_terms(text: str) -> list[str]:
    """Sinonimlarni kengaytiradi — qidiruv uchun barcha variantlar."""
    normalized = text.lower().strip()
    terms = {normalized} if normalized else set()

    for category, synonyms in CATEGORY_SYNONYMS.items():
        matched = any(syn in normalized for syn in synonyms) or category in normalized
        if matched:
            terms.add(category)
            terms.update(synonyms)

    for brand, category in BRAND_CATEGORIES.items():
        if brand in normalized:
            terms.add(brand)
            terms.add(category)

    return [t for t in terms if t]


def infer_product_metadata(product_name: str) -> dict[str, str]:
    normalized = product_name.lower()
    category = ""
    keywords: set[str] = set()

    for brand, cat in BRAND_CATEGORIES.items():
        if brand in normalized:
            category = cat
            keywords.add(brand)

    for cat, synonyms in CATEGORY_SYNONYMS.items():
        if cat in normalized or any(syn in normalized for syn in synonyms):
            category = category or cat
            keywords.update(synonyms[:3])

    if not keywords and category:
        keywords.add(category)

    return {
        "category": category,
        "keywords": ",".join(sorted(keywords)),
    }
