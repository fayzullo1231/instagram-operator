"""Rasm tahlili natijasini katalog qidiruviga tayyorlash."""

from __future__ import annotations

import re
from typing import Any

from shop.services.catalog_config import BRAND_CATEGORIES
from shop.utils.text import normalize_search_text
from shop.utils.transliterate import (
    build_catalog_search_text,
    canonical_brand,
    canonical_tokens,
    detect_product_grade,
    extract_volume_digits,
    latinize,
    normalize_product_weight,
)

PRODUCT_LINE_KEYWORDS: dict[str, list[str]] = {
    "tushonka": ["tushonka", "tushtonka", "gosht konservasi", "konserva"],
    "qoy": ["qoy", "qo'y", "baranina", "mutton"],
    "bonka": ["bonka", "banka"],
    "malako": ["malako", "moloko", "sgushchenka", "sgushchennoe", "sgushenka", "сгущенка"],
    "uni": ["uni", "un", "bugdoy", "bugdoyn", "flour", "мука", "мyka"],
}


PRODUCT_TYPE_ALIASES: dict[str, str] = {
    "podsolnechnoe maslo": "yog",
    "podslnechnoe maslo": "yog",
    "kungaboqar yog": "yog",
    "kungaboqar yogi": "yog",
    "sgushchennoe moloko": "malako",
    "sgushchenka": "malako",
    "sguschenka": "malako",
    "sgushenka": "malako",
    "condensed milk": "malako",
    "sut konsentrirovannoe": "malako",
    "podsolnechnoe": "yog",
    "rafinirovannoe": "yog",
    "dezodorirovannoe": "yog",
}


def _resolve_product_type(raw: str) -> str:
    normalized = latinize(raw) or normalize_search_text(raw)
    if not normalized:
        return ""
    line = detect_product_line(normalized)
    if line:
        return line
    for alias, resolved in PRODUCT_TYPE_ALIASES.items():
        if alias in normalized:
            return resolved
    return normalized


def detect_product_line(text: str) -> str:
    normalized = latinize(text) or normalize_search_text(text)
    if not normalized:
        return ""
    padded = f" {normalized} "
    for line, keywords in PRODUCT_LINE_KEYWORDS.items():
        for keyword in keywords:
            key = latinize(keyword) or keyword
            if len(key) <= 3:
                if f" {key} " in padded or padded.startswith(f"{key} ") or padded.endswith(f" {key}"):
                    return line
            elif key in normalized or keyword in normalized:
                return line
    return ""


def _normalize_weight(value: object, *context_parts: str) -> str:
    return normalize_product_weight(value, *context_parts)


def _clean_product_name(brand: str, name: str) -> str:
    brand_norm = latinize(brand)
    name_norm = latinize(name)
    if not name_norm:
        return ""
    if brand_norm and name_norm == brand_norm:
        return ""
    if brand_norm and name_norm.startswith(f"{brand_norm} "):
        remainder = name_norm[len(brand_norm) :].strip()
        if remainder == brand_norm:
            return ""
        return remainder
    return name_norm


def normalize_image_hint(hint: dict[str, Any]) -> dict[str, Any]:
    """Vision JSON ni tozalash — mahsulotni aniqlash, katalog qidiruv so'rovlari."""
    normalized = dict(hint)
    brand_raw = str(normalized.get("brand") or "").strip()
    identified = str(normalized.get("identified_product") or "").strip()
    product_type_raw = str(normalized.get("product_type") or "").strip()
    visible_raw = str(normalized.get("visible_text") or "").strip()
    name_raw = str(normalized.get("product_name") or "").strip()
    catalog_query = str(normalized.get("catalog_search_query") or "").strip()
    context_parts = [part for part in (identified, product_type_raw, name_raw, visible_raw, brand_raw) if part]
    weight = _normalize_weight(
        normalized.get("weight_grams") or normalized.get("weight") or normalized.get("package_size"),
        *context_parts,
    )
    grade = detect_product_grade(
        " ".join(part for part in (identified, product_type_raw, name_raw, normalized.get("category") or "") if part)
    )

    brand = canonical_brand(brand_raw) or (latinize(brand_raw).split()[0] if brand_raw else "")
    visible_latin = latinize(visible_raw)
    name = _clean_product_name(brand_raw, name_raw)
    if name:
        name = _resolve_product_type(name) if not detect_product_line(name) else name
        name = " ".join(canonical_tokens(name)) or latinize(name)
    if name and normalize_search_text(name) == normalize_search_text(brand):
        name = ""

    product_line = _resolve_product_type(product_type_raw)
    if not product_line:
        product_line = detect_product_line(identified) or detect_product_line(name_raw) or detect_product_line(name)
    if product_line and (not name or name in {"sguschenka", "sgushchenka", "moloko", "yog"}):
        if product_line not in {"yog"} or not name:
            name = product_line if product_line != "yog" else name

    if not name and product_line and product_line != "yog":
        name = product_line
    elif not name and identified:
        name = _clean_product_name(brand_raw, identified)
        if weight and weight in re.sub(r"[^\d]", "", normalize_search_text(name)):
            name = re.sub(r"\b\d+\b", "", name).strip()
        name = _resolve_product_type(name) or name

    if not product_line:
        product_line = detect_product_line(name) or _resolve_product_type(name)
    if not product_line and brand:
        brand_norm = normalize_search_text(brand)
        default_category = BRAND_CATEGORIES.get(brand_norm, "")
        if default_category in PRODUCT_LINE_KEYWORDS:
            product_line = default_category

    if name and normalize_search_text(name) == normalize_search_text(product_line):
        name = product_line

    queries: list[str] = []
    if catalog_query:
        cleaned = build_catalog_search_text(catalog_query)
        if cleaned:
            queries.append(cleaned)

    for item in normalized.get("search_queries") or []:
        cleaned = build_catalog_search_text(str(item).strip())
        if cleaned:
            queries.append(cleaned)

    brand_norm = normalize_search_text(brand)
    if brand and name and weight:
        queries.append(f"{brand_norm} {name} {weight}")
    if brand and product_line and weight and product_line != "yog":
        queries.append(f"{brand_norm} {product_line} {weight}")
    if brand and name:
        queries.append(f"{brand_norm} {name}")
    if brand and weight:
        queries.append(f"{brand_norm} {weight}")
    if brand and product_line and product_line != "yog":
        queries.append(f"{brand_norm} {product_line}")
    if brand and weight and grade == "vs":
        queries.append(f"{brand_norm} {weight} v s")
    if brand and weight and product_line == "uni":
        queries.append(f"{brand_norm} {weight} kg")

    seen: set[str] = set()
    unique_queries: list[str] = []
    for query in queries:
        key = normalize_search_text(query)
        if not key or key in seen:
            continue
        terms = [term for term in key.split() if len(term) > 1]
        if len(terms) < 2 and not (brand_norm and weight):
            continue
        seen.add(key)
        unique_queries.append(query)

    normalized["brand"] = brand
    normalized["product_name"] = name or product_line
    normalized["weight_grams"] = weight
    normalized["visible_text"] = visible_latin
    normalized["identified_product"] = latinize(identified) or identified
    normalized["search_queries"] = unique_queries
    normalized["_product_line"] = product_line
    normalized["_product_grade"] = grade
    return normalized


def format_detected_label(hint: dict[str, Any]) -> str:
    identified = str(hint.get("identified_product") or "").strip()
    if identified:
        return identified

    brand = str(hint.get("brand") or "").strip()
    name = str(hint.get("product_name") or "").strip()
    weight = str(hint.get("weight_grams") or hint.get("weight") or "").strip()
    product_line = str(hint.get("_product_line") or "").strip()

    if name and normalize_search_text(name) == normalize_search_text(brand):
        name = product_line or ""

    display_name = name or product_line
    parts: list[str] = []
    if brand:
        parts.append(brand.upper() if len(brand) <= 5 else brand.title())
    if display_name and normalize_search_text(display_name) != normalize_search_text(brand):
        parts.append(display_name)

    label = " ".join(parts).strip()
    grade = str(hint.get("_product_grade") or "").strip()
    if grade == "vs" and "v/s" not in label.lower() and "v s" not in label.lower():
        label = f"{label} v/s".strip() if label else "v/s"
    if weight:
        label = f"{label} {weight} kg".strip() if product_line == "uni" and weight else f"{label} {weight}".strip()
    return label
