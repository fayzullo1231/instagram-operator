import re

from shop.services.operator_prompts import NOT_FOUND_REPLY
from shop.services.product_search import SearchMatch
from shop.utils.text import format_price


class ResponseBuilder:
    AVAILABILITY_KEYWORDS = {"bormi", "bor", "mavjud", "qolgan", "qoldimi", "borimi"}
    CHANNEL_DM = "dm"
    CHANNEL_COMMENT = "comment"

    @classmethod
    def build(
        cls,
        message: str,
        matches: list[SearchMatch],
        is_single: bool,
        *,
        channel: str = CHANNEL_DM,
        is_category_match: bool = False,
        category: str = "",
    ) -> str:
        if not matches:
            return NOT_FOUND_REPLY

        asks_availability = cls._asks_availability(message)
        include_prices = channel == cls.CHANNEL_DM

        if is_category_match or (len(matches) > 1 and category):
            return cls._category_list(matches, category or matches[0].product.category, include_prices)

        if is_single:
            return cls._single_match(matches[0], asks_availability, include_prices)

        return cls._multiple_matches(matches, asks_availability, include_prices)

    @classmethod
    def build_dm_details(
        cls,
        message: str,
        matches: list[SearchMatch],
        is_single: bool,
        *,
        is_category_match: bool = False,
        category: str = "",
    ) -> str:
        return cls.build(
            message,
            matches,
            is_single,
            channel=cls.CHANNEL_DM,
            is_category_match=is_category_match,
            category=category,
        )

    @classmethod
    def _asks_availability(cls, message: str) -> bool:
        words = set(re.findall(r"\w+", message.lower()))
        return bool(words & cls.AVAILABILITY_KEYWORDS)

    @classmethod
    def _category_list(
        cls,
        matches: list[SearchMatch],
        category: str,
        include_prices: bool,
    ) -> str:
        names = [m.product.product_name for m in matches]
        display_category = category or "mahsulot"
        lines = [f"• {name}" for name in names]
        body = (
            f"✅ Bizda quyidagi {display_category} mahsulotlari mavjud:\n\n"
            + "\n".join(lines)
            + "\n\nQaysi biri qiziqtiryapti?"
        )
        if include_prices:
            price_lines = [
                f"• {m.product.product_name} — {format_price(m.product.price)}"
                for m in matches
            ]
            body = (
                f"✅ Bizda quyidagi {display_category} mahsulotlari mavjud:\n\n"
                + "\n".join(price_lines)
                + "\n\nQaysi biri qiziqtiryapti?"
            )
        return body

    @classmethod
    def _single_match(
        cls,
        match: SearchMatch,
        asks_availability: bool,
        include_prices: bool,
    ) -> str:
        product = match.product
        if not include_prices:
            return f"✅ {product.product_name} katalogimizda mavjud.\n\nBatafsil ma'lumot uchun Direct yozing."

        price_str = format_price(product.price)

        if asks_availability:
            return (
                f"Ha, bizda {product.product_name} mavjud. Narxi {price_str}.\n\n"
                f"Yana savollaringiz bo'lsa bemalol yozing."
            )

        return (
            f"{product.product_name} narxi {price_str}.\n\n"
            f"Yana savollaringiz bo'lsa bemalol yozing."
        )

    @classmethod
    def _multiple_matches(
        cls,
        matches: list[SearchMatch],
        asks_availability: bool,
        include_prices: bool,
    ) -> str:
        if not include_prices:
            lines = [f"• {m.product.product_name}" for m in matches]
            return (
                "Siz quyidagi mahsulotlardan qaysi birini nazarda tutyapsiz?\n\n"
                + "\n".join(lines)
                + "\n\nIltimos aniqlashtirib yozing."
            )

        lines = [
            f"• {m.product.product_name} — {format_price(m.product.price)}"
            for m in matches
        ]
        intro = (
            "Bizda quyidagi mahsulotlar mavjud:\n\n"
            if asks_availability
            else "Siz quyidagi mahsulotlardan qaysi birini nazarda tutyapsiz?\n\n"
        )
        outro = (
            "\n\nYana savollaringiz bo'lsa bemalol yozing."
            if asks_availability
            else "\n\nIltimos aniqlashtirib yozing."
        )
        return intro + "\n".join(lines) + outro
