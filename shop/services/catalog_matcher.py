"""OpenAI yordamida katalogdan rasm bo'yicha mahsulot tanlash."""

from __future__ import annotations

import json
import logging
import re

from django.conf import settings
from openai import OpenAI
from rapidfuzz import fuzz, process

from shop.models import Product
from shop.services.image_hint import format_detected_label
from shop.services.operator_prompts import IMAGE_CATALOG_MATCH_PROMPT
from shop.services.product_search import SearchMatch, SearchResult
from shop.utils.text import normalize_search_text
from shop.utils.transliterate import build_catalog_search_text, extract_volume_digits, latinize

logger = logging.getLogger(__name__)


class CatalogMatcherService:
    def __init__(self, client: OpenAI | None = None, model: str | None = None) -> None:
        self.client = client
        self.model = model or settings.OPENAI_MODEL

    def find_candidates(self, hint: dict, *, limit: int = 40) -> list[Product]:
        products = list(Product.objects.all().order_by("product_name"))
        if not products:
            return []

        weight = extract_volume_digits(str(hint.get("weight_grams") or hint.get("weight") or hint.get("package_size") or ""))
        search_text = build_catalog_search_text(
            str(hint.get("catalog_search_query") or ""),
            str(hint.get("identified_product") or ""),
            str(hint.get("brand") or ""),
            str(hint.get("product_name") or ""),
            " ".join(str(item) for item in hint.get("search_queries") or []),
        )
        if weight:
            by_weight = [
                product
                for product in products
                if weight in re.sub(r"[^\d]", "", normalize_search_text(product.product_name))
            ]
            if by_weight:
                products = by_weight

        if not search_text:
            return products[:limit]

        choices = {
            product.id: latinize(f"{product.product_name} {product.keywords}")
            for product in products
        }
        results = process.extract(search_text, choices, scorer=fuzz.WRatio, limit=limit)
        ranked_ids = [product_id for _, score, product_id in results if score >= 45]
        if not ranked_ids:
            return products[: min(limit, 15)]

        product_map = {product.id: product for product in products}
        return [product_map[product_id] for product_id in ranked_ids if product_id in product_map]

    def match_with_ai(self, hint: dict, detected_label: str = "") -> SearchResult:
        if not self.client:
            return SearchResult(matches=[])

        candidates = self.find_candidates(hint)
        if not candidates:
            return SearchResult(matches=[])

        label = detected_label or format_detected_label(hint) or build_catalog_search_text(
            str(hint.get("catalog_search_query") or ""),
            str(hint.get("identified_product") or ""),
            str(hint.get("brand") or ""),
            str(hint.get("product_name") or ""),
        )
        catalog_lines = [
            f"{product.id}|{product.product_name}|{int(product.price)}"
            for product in candidates[:35]
        ]

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": IMAGE_CATALOG_MATCH_PROMPT},
                    {
                        "role": "user",
                        "content": (
                            f"Rasmdan aniqlangan mahsulot: {label}\n"
                            f"Qo'shimcha ma'lumot: {json.dumps(hint, ensure_ascii=False)}\n\n"
                            "Katalog:\n"
                            + "\n".join(catalog_lines)
                        ),
                    },
                ],
                temperature=0.0,
                max_tokens=120,
                response_format={"type": "json_object"},
            )
            data = json.loads(response.choices[0].message.content or "{}")
        except Exception as exc:
            logger.warning("AI katalog moslashtirishda xato: %s", exc)
            return SearchResult(matches=[])

        if not data.get("found"):
            return SearchResult(matches=[])

        similarity = float(data.get("similarity") or 0)
        if similarity and similarity < settings.IMAGE_MATCH_MIN_SCORE:
            logger.info(
                "AI katalog moslik yetarli emas: %s < %s",
                similarity,
                settings.IMAGE_MATCH_MIN_SCORE,
            )
            return SearchResult(matches=[])

        product_id = data.get("product_id")
        product_name = str(data.get("product_name") or "").strip()
        product = None
        if product_id is not None:
            product = Product.objects.filter(id=product_id).first()
        if not product and product_name:
            product = Product.objects.filter(product_name__iexact=product_name).first()
        if not product:
            return SearchResult(matches=[])

        logger.info("AI katalog moslashtirish: '%s'", product.product_name)
        return SearchResult(
            matches=[SearchMatch(product=product, score=95.0, match_type="ai_catalog")]
        )

    def match_by_fuzzy(self, hint: dict, *, min_score: int | None = None) -> SearchResult:
        threshold = settings.IMAGE_MATCH_MIN_SCORE if min_score is None else min_score
        products = list(Product.objects.all().order_by("product_name"))
        if not products:
            return SearchResult(matches=[])

        search_text = build_catalog_search_text(
            str(hint.get("catalog_search_query") or ""),
            str(hint.get("identified_product") or ""),
            str(hint.get("brand") or ""),
            str(hint.get("product_name") or ""),
            " ".join(str(item) for item in hint.get("search_queries") or []),
        )
        if not search_text:
            return SearchResult(matches=[])

        weight = extract_volume_digits(
            str(hint.get("weight_grams") or hint.get("weight") or hint.get("package_size") or "")
        )
        if weight:
            filtered = [
                product
                for product in products
                if weight in re.sub(r"[^\d]", "", normalize_search_text(product.product_name))
            ]
            if filtered:
                products = filtered

        choices = {
            product.id: latinize(f"{product.product_name} {product.keywords}")
            for product in products
        }
        results = process.extract(search_text, choices, scorer=fuzz.WRatio, limit=1)
        if not results:
            return SearchResult(matches=[])

        _, score, product_id = results[0]
        if score < threshold:
            logger.info("Rasm fuzzy moslik yetarli emas: %s < %s", score, threshold)
            return SearchResult(matches=[])

        product = Product.objects.filter(id=product_id).first()
        if not product:
            return SearchResult(matches=[])

        logger.info("Rasm fuzzy moslashtirish: '%s' (ball=%s)", product.product_name, score)
        return SearchResult(
            matches=[SearchMatch(product=product, score=float(score), match_type="fuzzy_image")]
        )
