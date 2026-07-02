import logging
import re
from dataclasses import dataclass

from django.conf import settings
from rapidfuzz import fuzz, process

from shop.models import Product
from shop.services.catalog_config import BRAND_CATEGORIES, canonical_category, expand_search_terms
from shop.services.image_hint import format_detected_label, normalize_image_hint
from shop.utils.text import extract_search_keywords, normalize_search_text
from shop.utils.transliterate import latinize, product_matches_grade, product_name_latin, weights_match

logger = logging.getLogger(__name__)

_CATALOG_OPTIONAL_LINES = frozenset({"yog", ""})


@dataclass
class SearchMatch:
    product: Product
    score: float
    match_type: str = "fuzzy"


@dataclass
class SearchResult:
    matches: list[SearchMatch]
    is_category_match: bool = False
    category: str = ""


class ProductSearchService:
    def __init__(self) -> None:
        self.min_similarity = settings.FUZZ_MIN_SIMILARITY
        self.top_n = settings.FUZZ_TOP_N

    def search(self, query: str, *, allow_category: bool = True) -> SearchResult:
        products = list(Product.objects.all().order_by("product_name"))
        if not products:
            logger.warning("Qidiruv uchun mahsulotlar topilmadi")
            return SearchResult(matches=[])

        search_text = extract_search_keywords(query)
        if not search_text:
            logger.debug("Qidiruv kalit so'z yo'q: '%s'", query)
            return SearchResult(matches=[])

        logger.debug("Qidiruv matni: '%s' (asl: '%s')", search_text, query)
        terms = expand_search_terms(search_text)
        category = ""
        if allow_category:
            category = canonical_category(search_text) or ""
            if not category:
                for term in terms:
                    category = canonical_category(term)
                    if category:
                        break

        if allow_category and category:
            category_matches = self._category_matches(products, category)
            if category_matches:
                logger.info("Kategoriya qidiruvi: '%s', topildi=%d", category, len(category_matches))
                return SearchResult(
                    matches=category_matches[: self.top_n],
                    is_category_match=True,
                    category=category,
                )

        exact = self._exact_matches(products, search_text, terms)
        if exact:
            return SearchResult(matches=exact[: self.top_n])

        keyword = self._keyword_matches(products, search_text, terms)
        if keyword:
            return SearchResult(matches=keyword[: self.top_n])

        fuzzy = self._fuzzy_matches(products, search_text)
        logger.info("Qidiruv natijasi: query='%s', topildi=%d", query, len(fuzzy))
        return SearchResult(matches=fuzzy)

    def _category_matches(self, products: list[Product], category: str) -> list[SearchMatch]:
        matches: list[SearchMatch] = []
        seen: set[str] = set()

        for product in products:
            if product.category == category:
                key = normalize_search_text(product.product_name)
                if key in seen:
                    continue
                seen.add(key)
                matches.append(SearchMatch(product=product, score=100.0, match_type="category"))
                continue

            normalized = normalize_search_text(product.product_name)
            for brand, brand_cat in BRAND_CATEGORIES.items():
                if brand_cat == category and brand in normalized:
                    if normalized in seen:
                        continue
                    seen.add(normalized)
                    matches.append(SearchMatch(product=product, score=95.0, match_type="category"))
                    break

        return matches

    def _exact_matches(
        self,
        products: list[Product],
        search_text: str,
        terms: list[str],
    ) -> list[SearchMatch]:
        normalized_query = normalize_search_text(search_text)
        query_terms = set(terms + [normalized_query])
        matches: list[SearchMatch] = []

        for product in products:
            normalized_name = normalize_search_text(product.product_name)
            if normalized_name in query_terms or normalized_query == normalized_name:
                matches.append(SearchMatch(product=product, score=100.0, match_type="exact"))
            elif normalized_query in normalized_name or normalized_name in normalized_query:
                matches.append(SearchMatch(product=product, score=98.0, match_type="exact"))

        return matches

    def _keyword_matches(
        self,
        products: list[Product],
        search_text: str,
        terms: list[str],
    ) -> list[SearchMatch]:
        normalized_query = normalize_search_text(search_text)
        query_terms = set(terms + normalized_query.split())
        matches: list[SearchMatch] = []

        for product in products:
            haystack = normalize_search_text(
                f"{product.product_name} {product.keywords} {product.category}"
            )
            if any(term in haystack for term in query_terms if len(term) > 2):
                matches.append(SearchMatch(product=product, score=90.0, match_type="keyword"))

        return matches

    def _fuzzy_matches(
        self,
        products: list[Product],
        search_text: str,
        *,
        min_similarity: int | None = None,
    ) -> list[SearchMatch]:
        threshold = self.min_similarity if min_similarity is None else min_similarity
        choices = {
            p.id: normalize_search_text(f"{p.product_name} {p.keywords} {p.category}")
            for p in products
        }
        name_map = {p.id: p for p in products}

        results = process.extract(
            search_text,
            choices,
            scorer=fuzz.WRatio,
            limit=self.top_n * 3,
        )

        matches: list[SearchMatch] = []
        seen_names: set[str] = set()

        for _, score, product_id in results:
            if score < threshold:
                continue
            product = name_map.get(product_id)
            if not product:
                continue
            normalized_name = normalize_search_text(product.product_name)
            if normalized_name in seen_names:
                continue
            seen_names.add(normalized_name)
            matches.append(SearchMatch(product=product, score=float(score), match_type="fuzzy"))
            if len(matches) >= self.top_n:
                break

        return matches

    @staticmethod
    def is_single_match(matches: list[SearchMatch]) -> bool:
        if not matches:
            return False
        if len(matches) == 1:
            return True

        top = matches[0].score
        second = matches[1].score if len(matches) > 1 else 0.0

        if top >= 85 and (top - second) >= 15:
            return True

        return False

    def search_from_image_hint(self, hint: dict) -> SearchResult:
        """Rasm tahlilidan kelgan ma'lumotlar bo'yicha qattiq qidiruv."""
        hint = normalize_image_hint(hint)
        confidence = str(hint.get("confidence") or "").lower()
        if confidence == "low":
            logger.info("Rasm tahlili confidence=low — qidiruv o'tkazilmaydi")
            return SearchResult(matches=[])

        queries = hint.get("search_queries") or []
        if not queries:
            logger.info("Rasm uchun yetarli qidiruv so'rovi yo'q: %s", hint)
            return SearchResult(matches=[])

        brand = normalize_search_text(str(hint.get("brand") or ""))
        weight = self._normalize_weight(hint.get("weight_grams") or hint.get("weight"))
        direct = self._direct_catalog_match(hint)
        if direct:
            logger.info("Rasm qidiruvi (to'g'ridan): '%s'", direct.product.product_name)
            return SearchResult(matches=[direct])

        candidates: dict[int, SearchMatch] = {}

        for query in queries:
            result = self._search_for_image(query, min_fuzz=settings.IMAGE_SEARCH_MIN_FUZZ, brand=brand)
            if not result.matches:
                continue
            if weight:
                result = self._prefer_weight_match(result, weight)
            ranked = self._rank_by_image_hint(result.matches, hint)
            for match in ranked:
                product_id = match.product.id
                existing = candidates.get(product_id)
                if not existing or match.score > existing.score:
                    candidates[product_id] = match

        if not candidates:
            return SearchResult(matches=[])

        ordered = sorted(candidates.values(), key=lambda m: m.score, reverse=True)
        top = ordered[0]
        second_score = ordered[1].score if len(ordered) > 1 else 0.0

        if top.score < settings.IMAGE_MATCH_MIN_SCORE:
            logger.info(
                "Rasm qidiruvi: eng yaxshi ball yetarli emas (%s < %s)",
                top.score,
                settings.IMAGE_MATCH_MIN_SCORE,
            )
            return SearchResult(matches=[])

        if len(ordered) > 1 and (top.score - second_score) < 12:
            resolved = self._resolve_image_ambiguity(ordered, hint)
            if not resolved:
                logger.info(
                    "Rasm qidiruvi: bir nechta yaqin variant (%s vs %s)",
                    top.score,
                    second_score,
                )
                return SearchResult(matches=[])
            ordered = resolved

        winner = ordered[0]
        logger.info(
            "Rasm qidiruvi topildi: '%s' (ball=%s)",
            winner.product.product_name,
            winner.score,
        )
        return SearchResult(matches=[winner])

    def _brand_in_text(self, text: str) -> str:
        normalized = normalize_search_text(text)
        for brand in BRAND_CATEGORIES:
            if brand in normalized:
                return brand
        for brand in BRAND_CATEGORIES:
            if brand in normalized.split():
                return brand
        words = normalized.split()
        for word in words:
            if word in BRAND_CATEGORIES:
                return word
        return ""

    def _filter_image_matches(
        self,
        matches: list[SearchMatch],
        brand: str,
    ) -> list[SearchMatch]:
        if not brand:
            return matches
        filtered: list[SearchMatch] = []
        for match in matches:
            haystack = normalize_search_text(
                f"{match.product.product_name} {match.product.keywords}"
            )
            if brand in haystack:
                filtered.append(match)
        return filtered

    def _keyword_matches_for_image(
        self,
        products: list[Product],
        terms: list[str],
        brand: str,
    ) -> list[SearchMatch]:
        significant = [term for term in terms if len(term) > 2 and not term.isdigit()]
        weight_terms = [term for term in terms if term.isdigit() and len(term) >= 3]
        if not significant and not brand:
            return []

        min_hits = min(2, len(significant)) if len(significant) >= 2 else max(1, len(significant))
        matches: list[SearchMatch] = []

        for product in products:
            haystack = normalize_search_text(
                f"{product.product_name} {product.keywords} {product.category}"
            )
            if brand and brand not in haystack:
                continue
            matched = [term for term in significant if term in haystack]
            if len(matched) < min_hits:
                continue
            if weight_terms:
                if not any(weights_match(weight, product.product_name) for weight in weight_terms):
                    continue
            matches.append(SearchMatch(product=product, score=90.0, match_type="keyword"))

        return matches

    def _direct_catalog_match(self, hint: dict) -> SearchMatch | None:
        brand = normalize_search_text(str(hint.get("brand") or ""))
        weight = self._normalize_weight(hint.get("weight_grams") or hint.get("weight"))
        product_line = normalize_search_text(str(hint.get("_product_line") or ""))
        grade = str(hint.get("_product_grade") or "")
        identified = latinize(str(hint.get("identified_product") or ""))
        name = latinize(str(hint.get("product_name") or ""))

        if not brand and not identified:
            return None

        label = " ".join(part for part in (brand, name or product_line, weight) if part).strip()
        compare_text = identified or label
        if grade == "vs":
            compare_text = f"{compare_text} v s"
        if not compare_text:
            return None

        products = list(Product.objects.all().order_by("product_name"))
        best_match: SearchMatch | None = None

        for product in products:
            haystack = product_name_latin(product.product_name)
            if brand and brand not in haystack:
                continue
            if weight:
                if not weights_match(weight, product.product_name):
                    continue
            if (
                product_line
                and product_line not in _CATALOG_OPTIONAL_LINES
                and product_line not in haystack
                and product_line not in latinize(product.keywords or "")
            ):
                if not (product_line == "uni" and brand in haystack):
                    continue
            if grade and not product_matches_grade(product.product_name, grade):
                continue

            score = float(fuzz.WRatio(compare_text, haystack))
            if product_line and product_line in haystack:
                score += 12
            if weight and weights_match(weight, product.product_name):
                score += 8
            if grade and product_matches_grade(product.product_name, grade):
                score += 15

            if not best_match or score > best_match.score:
                best_match = SearchMatch(product=product, score=score, match_type="catalog")

        if best_match and best_match.score >= 82:
            return best_match
        return None

    def _resolve_image_ambiguity(
        self,
        ordered: list[SearchMatch],
        hint: dict,
    ) -> list[SearchMatch]:
        product_line = normalize_search_text(str(hint.get("_product_line") or ""))
        identified = normalize_search_text(str(hint.get("identified_product") or ""))
        if not product_line and not identified:
            return []

        rescored: list[SearchMatch] = []
        for match in ordered[:5]:
            haystack = normalize_search_text(match.product.product_name)
            score = float(match.score)
            if product_line and product_line in haystack:
                score += 35
            if identified:
                overlap = sum(1 for token in identified.split() if len(token) > 2 and token in haystack)
                score += overlap * 10
            rescored.append(SearchMatch(product=match.product, score=score, match_type=match.match_type))

        rescored.sort(key=lambda item: item.score, reverse=True)
        if len(rescored) == 1:
            return rescored[:1]
        if rescored[0].score - rescored[1].score >= 10:
            return rescored[:1]
        return []

    def _search_for_image(self, query: str, *, min_fuzz: int, brand: str = "") -> SearchResult:
        products = list(Product.objects.all().order_by("product_name"))
        if not products:
            return SearchResult(matches=[])

        search_text = extract_search_keywords(query) or normalize_search_text(query)
        if not search_text:
            return SearchResult(matches=[])

        if not brand:
            brand = self._brand_in_text(search_text)

        terms = [term for term in normalize_search_text(search_text).split() if len(term) > 1]
        exact = self._filter_image_matches(
            self._exact_matches(products, search_text, terms),
            brand,
        )
        if exact:
            return SearchResult(matches=exact[: self.top_n])

        keyword = self._keyword_matches_for_image(products, terms, brand)
        if keyword:
            return SearchResult(matches=keyword[: self.top_n])

        fuzzy = self._filter_image_matches(
            self._fuzzy_matches(products, search_text, min_similarity=min_fuzz),
            brand,
        )
        return SearchResult(matches=fuzzy[: self.top_n])

    def _rank_by_image_hint(self, matches: list[SearchMatch], hint: dict) -> list[SearchMatch]:
        brand = normalize_search_text(str(hint.get("brand") or ""))
        name = latinize(str(hint.get("product_name") or ""))
        product_line = normalize_search_text(str(hint.get("_product_line") or ""))
        grade = str(hint.get("_product_grade") or "")
        weight = self._normalize_weight(hint.get("weight_grams") or hint.get("weight"))
        name_tokens = [
            token
            for token in name.split()
            if len(token) > 2 and token not in {brand, product_line}
        ]
        if product_line and product_line not in _CATALOG_OPTIONAL_LINES and product_line not in name_tokens:
            name_tokens.append(product_line)

        ranked: list[SearchMatch] = []
        for match in matches:
            if match.match_type == "category":
                continue

            haystack = product_name_latin(f"{match.product.product_name} {match.product.keywords}")
            score = float(match.score)

            if brand:
                score += 25 if brand in haystack else -30
            if weight:
                score += 20 if weights_match(weight, match.product.product_name) else -15
            if grade:
                score += 20 if product_matches_grade(match.product.product_name, grade) else -25
            if name_tokens:
                hits = sum(1 for token in name_tokens if token in haystack)
                score += hits * 12
                if hits == 0 and len(name_tokens) >= 2:
                    score -= 20

            ranked.append(SearchMatch(product=match.product, score=score, match_type=match.match_type))

        ranked.sort(key=lambda item: item.score, reverse=True)
        return ranked

    @staticmethod
    def _normalize_weight(value: object) -> str:
        from shop.utils.transliterate import _normalize_volume_string

        text = str(value or "").strip()
        if not text:
            return ""
        if re.search(r"[.,]", text):
            return _normalize_volume_string(text)
        return re.sub(r"[^\d]", "", text)

    def _prefer_weight_match(self, result: SearchResult, weight: str) -> SearchResult:
        if not weight or not result.matches:
            return result
        weighted = [
            m
            for m in result.matches
            if weights_match(weight, m.product.product_name)
        ]
        if weighted:
            return SearchResult(
                matches=weighted[: self.top_n],
                is_category_match=result.is_category_match,
                category=result.category,
            )
        return result
