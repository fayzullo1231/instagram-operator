"""Matn qidiruvi uchun ChatGPT: xato yozuvni to'g'rilash va natijani tekshirish."""

from __future__ import annotations

import json
import logging

from django.conf import settings
from openai import OpenAI

from shop.services.operator_prompts import SEARCH_CORRECTION_PROMPT, SEARCH_RESULT_VALIDATION_PROMPT
from shop.services.product_search import SearchMatch, SearchResult
from shop.utils.text import extract_search_keywords, normalize_search_text
from shop.utils.transliterate import latinize

logger = logging.getLogger(__name__)


class TextCatalogMatcherService:
    def __init__(self, client: OpenAI | None = None, model: str | None = None) -> None:
        self.client = client
        self.model = model or settings.OPENAI_MODEL

    def suggest_queries(self, message: str, *, tried: list[str] | None = None) -> list[str]:
        if not self.client:
            return []

        tried_set = {normalize_search_text(item) for item in (tried or [])}
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SEARCH_CORRECTION_PROMPT},
                    {"role": "user", "content": message},
                ],
                temperature=0.0,
                max_tokens=180,
                response_format={"type": "json_object"},
            )
            data = json.loads(response.choices[0].message.content or "{}")
        except Exception as exc:
            logger.warning("ChatGPT qidiruv to'g'rilashda xato: %s", exc)
            return []

        if data.get("skip"):
            return []

        queries: list[str] = []
        raw_items = data.get("search_queries") or []
        if isinstance(raw_items, list):
            for item in raw_items:
                if not isinstance(item, str) or not item.strip():
                    continue
                query = self._normalize_query(item)
                if query and normalize_search_text(query) not in tried_set and query not in queries:
                    queries.append(query)
        return queries

    def filter_matches(self, message: str, matches: list[SearchMatch]) -> SearchResult:
        if not matches:
            return SearchResult(matches=[])
        if not self.client:
            logger.info("ChatGPT yo'q — shubhali qidiruv natijasi rad etildi")
            return SearchResult(matches=[])

        catalog_lines = [
            f"{match.product.id}|{match.product.product_name}|{int(match.product.price)}"
            for match in matches[:20]
        ]
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SEARCH_RESULT_VALIDATION_PROMPT},
                    {
                        "role": "user",
                        "content": (
                            f"Foydalanuvchi so'rovi: {message}\n\n"
                            "Kandidat mahsulotlar:\n"
                            + "\n".join(catalog_lines)
                        ),
                    },
                ],
                temperature=0.0,
                max_tokens=160,
                response_format={"type": "json_object"},
            )
            data = json.loads(response.choices[0].message.content or "{}")
        except Exception as exc:
            logger.warning("ChatGPT natija tekshiruvida xato: %s", exc)
            return SearchResult(matches=[])

        if not data.get("confident"):
            logger.info("ChatGPT: qidiruv natijasi ishonchsiz — rad etildi")
            return SearchResult(matches=[])

        raw_ids = data.get("product_ids") or []
        if not isinstance(raw_ids, list):
            return SearchResult(matches=[])

        allowed_ids = {int(product_id) for product_id in raw_ids if str(product_id).isdigit()}
        if not allowed_ids:
            return SearchResult(matches=[])

        filtered = [match for match in matches if match.product.id in allowed_ids]
        if not filtered:
            return SearchResult(matches=[])

        logger.info("ChatGPT tasdiqladi: %d ta mahsulot", len(filtered))
        return SearchResult(matches=filtered)

    @staticmethod
    def _normalize_query(text: str) -> str:
        cleaned = extract_search_keywords(text) or latinize(text.strip())
        return latinize(cleaned) or cleaned
