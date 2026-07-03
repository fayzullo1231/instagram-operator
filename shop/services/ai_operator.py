import json
import logging
from dataclasses import dataclass, field

from django.conf import settings
from openai import OpenAI

from shop.services.operator_prompts import (
    ADDRESS_REPLY,
    COMMENT_ASK_DM_REPLY,
    COMMENT_INFO_REPLY,
    COMMENT_PRICE_REPLY,
    CONVERSATIONAL_PROMPT,
    DELIVERY_REPLY,
    GREETING_REPLY,
    HOURS_REPLY,
    IMAGE_ANALYSIS_PROMPT,
    IMAGE_FOUND_REPLY,
    INTENT_EXTRACTION_PROMPT,
    NOT_FOUND_FALLBACK,
    NOT_FOUND_REPLY,
    PHONE_REPLY,
    PRODUCT_NOT_FOUND_PROMPT,
    SYSTEM_PROMPT,
    THANKS_REPLY,
)
from shop.services.catalog_matcher import CatalogMatcherService
from shop.services.image_hint import format_detected_label, normalize_image_hint
from shop.services.product_search import ProductSearchService, SearchMatch, SearchResult
from shop.services.response_builder import ResponseBuilder
from shop.utils.image_fetch import fetch_image_as_data_url
from shop.utils.intents import Intent, detect_intent
from shop.utils.text import extract_search_keywords, is_conversational_message, is_greeting_only

logger = logging.getLogger(__name__)


@dataclass
class ChatResponse:
    reply: str
    matches: list[dict] = field(default_factory=list)
    dm_reply: str | None = None
    send_dm: bool = False


class AIOperatorService:
    def __init__(self) -> None:
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None
        self.model = settings.OPENAI_MODEL
        self.search_service = ProductSearchService()
        self.response_builder = ResponseBuilder()
        self.catalog_matcher = CatalogMatcherService(self.client, self.model)

    def process_message(
        self,
        message: str,
        *,
        channel: str = ResponseBuilder.CHANNEL_DM,
        image_url: str | None = None,
    ) -> ChatResponse:
        if image_url:
            return self._process_image(message, image_url, channel=channel)

        message = message.strip()
        if not message:
            return ChatResponse(reply=GREETING_REPLY)

        intent = detect_intent(message)
        if intent == Intent.GREETING or is_greeting_only(message):
            return ChatResponse(reply=self._answer_faq(message))
        if intent == Intent.THANKS:
            return ChatResponse(reply=self._answer_faq(message))
        if intent == Intent.ADDRESS:
            return ChatResponse(reply=ADDRESS_REPLY)
        if intent == Intent.PHONE:
            return ChatResponse(reply=PHONE_REPLY)
        if intent == Intent.HOURS:
            return ChatResponse(reply=HOURS_REPLY)
        if intent == Intent.DELIVERY:
            return ChatResponse(reply=DELIVERY_REPLY)

        if channel == ResponseBuilder.CHANNEL_COMMENT:
            if intent in (Intent.PRICE, Intent.COMMENT_LEAD):
                return self._comment_with_dm(message, intent)
            if intent in (Intent.AVAILABILITY, Intent.PRODUCT):
                return self._comment_product_lead(message)

        if is_conversational_message(message):
            return ChatResponse(reply=self._answer_faq(message))

        search_query = self._extract_search_query(message)
        if not search_query:
            if intent == Intent.PRICE:
                return ChatResponse(
                    reply="Qaysi mahsulot narxi kerak? Mahsulot nomini yozib yuboring."
                )
            if intent in (Intent.GENERAL, Intent.PRODUCT) or is_conversational_message(message):
                return ChatResponse(reply=self._answer_faq(message))
            return ChatResponse(reply=self._answer_faq(message))

        logger.info("AI qidiruv so'rovi: '%s' (asl xabar: '%s')", search_query, message)

        result = self.search_service.search(search_query)
        is_single = self.search_service.is_single_match(result.matches)

        if result.matches:
            reply = self.response_builder.build(
                message,
                result.matches,
                is_single,
                channel=channel,
                is_category_match=result.is_category_match,
                category=result.category,
            )
            return ChatResponse(
                reply=reply,
                matches=[self._match_to_dict(m) for m in result.matches],
            )

        if self._is_likely_product_query(message, intent, search_query):
            return ChatResponse(reply=self._answer_product_not_found(message))

        return ChatResponse(reply=self._answer_faq(message))

    def _comment_with_dm(self, message: str, intent: Intent) -> ChatResponse:
        public = COMMENT_PRICE_REPLY if intent == Intent.PRICE else COMMENT_INFO_REPLY
        search_query = self._extract_search_query(message) or extract_search_keywords(message)
        dm_reply = None

        if search_query:
            result = self.search_service.search(search_query)
            if result.matches:
                dm_reply = self.response_builder.build_dm_details(
                    message,
                    result.matches,
                    self.search_service.is_single_match(result.matches),
                    is_category_match=result.is_category_match,
                    category=result.category,
                )
            else:
                dm_reply = self._answer_product_not_found(message)
        elif intent == Intent.PRICE:
            dm_reply = "Qaysi mahsulot narxi kerak? Mahsulot nomini yozib yuboring."
        else:
            dm_reply = GREETING_REPLY

        return ChatResponse(reply=public, dm_reply=dm_reply, send_dm=True)

    def _comment_product_lead(self, message: str) -> ChatResponse:
        search_query = self._extract_search_query(message)
        if not search_query:
            return ChatResponse(
                reply=COMMENT_INFO_REPLY,
                dm_reply=GREETING_REPLY,
                send_dm=True,
            )

        result = self.search_service.search(search_query)
        if result.matches:
            dm_reply = self.response_builder.build_dm_details(
                message,
                result.matches,
                self.search_service.is_single_match(result.matches),
                is_category_match=result.is_category_match,
                category=result.category,
            )
            return ChatResponse(
                reply=COMMENT_INFO_REPLY,
                dm_reply=dm_reply,
                send_dm=True,
                matches=[self._match_to_dict(m) for m in result.matches],
            )

        return ChatResponse(
            reply=COMMENT_INFO_REPLY,
            dm_reply=self._answer_product_not_found(message),
            send_dm=True,
        )

    def _process_image(
        self,
        message: str,
        image_url: str,
        *,
        channel: str,
    ) -> ChatResponse:
        product_hint, analysis_ok = self._analyze_image(image_url, caption=message)
        if not analysis_ok or not product_hint:
            logger.info("Rasm tahlili muvaffaqiyatsiz — javob yuborilmaydi")
            return self._empty_reply()

        product_hint = normalize_image_hint(product_hint)
        confidence = str(product_hint.get("confidence") or "").lower()
        if confidence == "low":
            logger.info("Rasm confidence=low — javob yuborilmaydi")
            return self._empty_reply()

        detected_label = format_detected_label(product_hint)
        logger.info("Rasm tahlili: %s (confidence=%s)", product_hint, confidence or "n/a")

        result = self.search_service.search_from_image_hint(product_hint)
        if not result.matches and self.client:
            logger.info("Mahalliy qidiruv topilmadi — AI katalog qidiruvi")
            result = self.catalog_matcher.match_with_ai(product_hint, detected_label)
        if not result.matches:
            logger.info("AI katalog topilmadi — fuzzy 90%% qidiruv")
            result = self.catalog_matcher.match_by_fuzzy(product_hint)
        if not result.matches:
            logger.info(
                "Rasm katalogda mos mahsulot yo'q (>=90%%) — javob yuborilmaydi: %s",
                detected_label or "noma'lum",
            )
            return self._empty_reply()

        return self._image_catalog_reply(message, result, channel=channel)

    def _empty_reply(self) -> ChatResponse:
        return ChatResponse(reply="")

    def _image_catalog_reply(
        self,
        message: str,
        result: SearchResult,
        *,
        channel: str,
    ) -> ChatResponse:
        is_single = True
        if channel == ResponseBuilder.CHANNEL_COMMENT:
            dm_reply = self.response_builder.build_dm_details(
                message,
                result.matches,
                is_single,
            )
            return ChatResponse(
                reply=IMAGE_FOUND_REPLY,
                dm_reply=dm_reply,
                send_dm=True,
                matches=[self._match_to_dict(m) for m in result.matches],
            )

        product_reply = self.response_builder.build(
            message,
            result.matches,
            is_single,
            channel=channel,
        )
        reply = f"{IMAGE_FOUND_REPLY}\n\n{product_reply}"
        return ChatResponse(
            reply=reply,
            matches=[self._match_to_dict(m) for m in result.matches],
        )

    def _analyze_image(self, image_url: str, *, caption: str = "") -> tuple[dict | None, bool]:
        """(mahsulot ma'lumoti, tahlil muvaffaqiyatli bo'ldimi)"""
        if not self.client:
            return None, False

        data_url = fetch_image_as_data_url(image_url)
        if not data_url:
            return None, False

        user_text = (
            "Rasmdagi mahsulotni ko'ring va NIMA ekanligini to'liq aniqlang "
            "(brend + tur + hajm). Qadoq sloganlarini qidiruv uchun ishlatmang."
        )
        if caption.strip():
            user_text = (
                f"Mijoz xabari: {caption.strip()}\n\n"
                "Rasmdagi mahsulotni vizual tanib aniqlang — brend, mahsulot turi va hajm. "
                "Qadoqdagi reklama matnini emas, mahsulotning haqiqiy nomini qaytaring."
            )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": IMAGE_ANALYSIS_PROMPT},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": user_text},
                            {"type": "image_url", "image_url": {"url": data_url}},
                        ],
                    },
                ],
                temperature=0.0,
                max_tokens=400,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content or "{}"
            data = json.loads(content)
            confidence = str(data.get("confidence") or "").lower()
            has_hint = any(
                data.get(k)
                for k in (
                    "identified_product",
                    "catalog_search_query",
                    "product_name",
                    "brand",
                    "weight_grams",
                    "search_queries",
                )
            )
            if confidence == "low" or not has_hint:
                return data if has_hint else None, True
            return data, True
        except Exception as exc:
            logger.warning("Rasm tahlilida xato: %s", exc)
            return None, False

    def _is_likely_product_query(self, message: str, intent: Intent, search_query: str) -> bool:
        if intent in (Intent.PRICE, Intent.AVAILABILITY):
            return bool(search_query.strip())
        if intent != Intent.PRODUCT:
            return False
        keywords = [w for w in search_query.split() if len(w) > 2]
        return len(keywords) >= 1 and not is_conversational_message(message)

    def _answer_faq(self, message: str) -> str:
        return self._chat_reply(message, CONVERSATIONAL_PROMPT, fallback=GREETING_REPLY)

    def _answer_product_not_found(self, message: str) -> str:
        return self._chat_reply(message, PRODUCT_NOT_FOUND_PROMPT, fallback=NOT_FOUND_FALLBACK)

    def _chat_reply(self, message: str, system_prompt: str, *, fallback: str) -> str:
        if not self.client:
            return fallback
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message},
                ],
                temperature=0.4,
                max_tokens=300,
            )
            return (response.choices[0].message.content or fallback).strip()
        except Exception as exc:
            logger.warning("ChatGPT javobida xato: %s", exc)
            return fallback

    def _extract_search_query(self, message: str) -> str:
        local_keywords = extract_search_keywords(message)
        if not local_keywords:
            return ""

        if not self.client:
            return local_keywords

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": INTENT_EXTRACTION_PROMPT},
                    {"role": "user", "content": message},
                ],
                temperature=0.1,
                max_tokens=150,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content or "{}"
            data = json.loads(content)
            if data.get("intent") in ("greeting", "thanks", "general"):
                return ""
            category = data.get("category", "")
            if isinstance(category, str) and category.strip():
                return category.strip()
            search_query = data.get("search_query", local_keywords)
            if isinstance(search_query, str) and search_query.strip():
                refined = extract_search_keywords(search_query.strip())
                return refined or search_query.strip()
        except Exception as exc:
            logger.warning("OpenAI qidiruv ajratishda xato: %s — mahalliy qidiruv", exc)

        return local_keywords

    @staticmethod
    def _match_to_dict(match: SearchMatch) -> dict:
        product = match.product
        return {
            "product": {
                "id": product.id,
                "external_id": product.external_id,
                "product_name": product.product_name,
                "category": product.category,
                "keywords": product.keywords,
                "barcode": product.barcode,
                "price": product.price,
                "balance": product.balance,
                "source": product.source,
                "updated_at": product.updated_at.isoformat() if product.updated_at else None,
            },
            "score": match.score,
            "match_type": match.match_type,
        }
