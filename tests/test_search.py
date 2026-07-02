"""Mahsulot qidiruv va javob yaratish testlari."""

from unittest.mock import patch

from shop.services.image_hint import normalize_image_hint
from shop.services.product_search import ProductSearchService, SearchMatch
from shop.services.response_builder import ResponseBuilder
from shop.utils.intents import Intent, detect_intent
from shop.utils.text import extract_search_keywords, format_price, is_greeting_only


_id_counter = 0


class FakeProduct:
    def __init__(
        self,
        name: str,
        price: float,
        balance: float = 10.0,
        category: str = "",
        keywords: str = "",
        product_id: int | None = None,
    ):
        global _id_counter
        _id_counter += 1
        self.id = product_id if product_id is not None else _id_counter
        self.external_id = "test-1"
        self.product_name = name
        self.category = category
        self.keywords = keywords
        self.barcode = "1000"
        self.price = price
        self.balance = balance
        self.source = "mdokon"
        self.updated_at = None


def _product(
    name: str,
    price: float,
    balance: float = 10.0,
    category: str = "",
    keywords: str = "",
) -> FakeProduct:
    return FakeProduct(name, price, balance, category, keywords)


def test_format_price():
    assert format_price(5000) == "5 000 so'm"
    assert format_price(50000) == "50 000 so'm"
    assert format_price(500000) == "500 000 so'm"
    assert format_price(5000000) == "5 000 000 so'm"


def test_extract_keywords():
    assert "altyn" in extract_search_keywords("altyn dan un qancha")
    assert "qand" in extract_search_keywords("qand bormi")
    assert extract_search_keywords("Assalomu alaykum") == ""
    assert extract_search_keywords("salom") == ""


def test_greeting_only():
    assert is_greeting_only("Assalomu alaykum") is True
    assert is_greeting_only("salom") is True
    assert is_greeting_only("qand bormi") is False


def test_detect_intent():
    assert detect_intent("assalomu alaykum") == Intent.GREETING
    assert detect_intent("rahmat") == Intent.THANKS
    assert detect_intent("manzil qayerda") == Intent.ADDRESS
    assert detect_intent("narx qancha") == Intent.PRICE


def test_single_match_response():
    match = SearchMatch(product=_product("Altyn Dan 50кг в/с", 375000), score=95.0)
    reply = ResponseBuilder.build("altyn dan 50kg un qancha", [match], is_single=True)
    assert "375 000 so'm" in reply


def test_multiple_match_response():
    matches = [
        SearchMatch(product=_product("Altyn Dan 50кг в/с", 375000), score=80.0),
        SearchMatch(product=_product("Altyn Dan 50кг 1/с", 280000), score=78.0),
    ]
    reply = ResponseBuilder.build("altyn dan un", matches, is_single=False)
    assert "qaysi birini nazarda tutyapsiz" in reply
    assert "375 000 so'm" in reply


def test_comment_response_hides_price():
    match = SearchMatch(product=_product("Ansor tushonka", 25000, category="tushonka"), score=95.0)
    reply = ResponseBuilder.build(
        "ansor bormi",
        [match],
        is_single=True,
        channel=ResponseBuilder.CHANNEL_COMMENT,
    )
    assert "so'm" not in reply
    assert "Ansor" in reply


def test_category_list_response():
    matches = [
        SearchMatch(product=_product("Ansor", 10000, category="tushonka"), score=100.0, match_type="category"),
        SearchMatch(product=_product("Poyqadam", 12000, category="tushonka"), score=100.0, match_type="category"),
    ]
    reply = ResponseBuilder.build(
        "tushonka bormi",
        matches,
        is_single=False,
        is_category_match=True,
        category="tushonka",
    )
    assert "Ansor" in reply
    assert "Poyqadam" in reply
    assert "Qaysi biri qiziqtiryapti" in reply


def test_not_found_response():
    reply = ResponseBuilder.build("xyz mahsulot", [], is_single=False)
    assert "topilmadi" in reply


def test_is_single_match():
    service = ProductSearchService()
    one = [SearchMatch(product=_product("Test", 1000), score=90)]
    two = [
        SearchMatch(product=_product("A", 1000), score=80),
        SearchMatch(product=_product("B", 2000), score=75),
    ]
    clear = [
        SearchMatch(product=_product("A", 1000), score=95),
        SearchMatch(product=_product("B", 2000), score=70),
    ]
    assert service.is_single_match(one) is True
    assert service.is_single_match(two) is False
    assert service.is_single_match(clear) is True


@patch("shop.services.product_search.Product.objects.all")
def test_image_search_zateya_oil_identified_not_ocr(mock_all):
    products = [
        FakeProduct("Zateya 0.5l", 13000),
        FakeProduct("Zateya 1.8l", 45000),
        FakeProduct("Zateya 5l", 125000),
    ]
    mock_all.return_value.order_by.return_value = products
    service = ProductSearchService()
    hint = normalize_image_hint(
        {
            "confidence": "high",
            "identified_product": "Zateya kungaboqar yog'i 5 litr",
            "product_type": "kungaboqar yog",
            "brand": "Zateya",
            "product_name": "kungaboqar yog",
            "weight_grams": "5",
            "package_size": "5l",
            "catalog_search_query": "zateya 5l",
            "visible_text": (
                "chistoe i zdorovoe maslo zateya s beregov dona "
                "podsolnechnoe maslo rafinirovannoe dezodorirovannoe 5l"
            ),
            "search_queries": ["zateya 5l", "zateya kungaboqar yog 5l"],
        }
    )
    assert "chistoe" not in " ".join(hint["search_queries"]).lower()
    result = service.search_from_image_hint(hint)
    assert len(result.matches) == 1
    assert result.matches[0].product.product_name == "Zateya 5l"


def test_image_hint_queries_skip_weak_terms():
    hint = normalize_image_hint(
        {"brand": "ansor", "category": "tushonka", "product_name": "", "search_queries": []}
    )
    assert hint.get("search_queries") == []


def test_image_search_rejects_low_confidence():
    service = ProductSearchService()
    result = service.search_from_image_hint({"confidence": "low", "brand": "ansor"})
    assert result.matches == []


@patch("shop.services.product_search.Product.objects.all")
def test_image_search_poyqadam_duplicate_brand(mock_all):
    products = [
        FakeProduct("POYQADAM BONKA 430 gr", 57500, category="tushonka"),
        FakeProduct("POYQADAM QOY 325 gr", 51000, category="tushonka"),
        FakeProduct("POYQADAM TUSHONKA 325 gr", 56600, category="tushonka"),
    ]
    mock_all.return_value.order_by.return_value = products
    service = ProductSearchService()
    hint = normalize_image_hint(
        {
            "confidence": "high",
            "brand": "POYQADAM",
            "product_name": "POYQADAM",
            "weight_grams": "325",
            "visible_text": "POYQADAM TUSHONKA 325 gr",
            "search_queries": ["POYQADAM POYQADAM 325"],
        }
    )
    result = service.search_from_image_hint(hint)
    assert len(result.matches) == 1
    assert result.matches[0].product.product_name == "POYQADAM TUSHONKA 325 gr"


@patch("shop.services.product_search.Product.objects.all")
def test_image_search_mari_malako_cyrillic(mock_all):
    products = [
        FakeProduct("MARI MALAKO 350 ml", 11000),
        FakeProduct("MARI MALAKO 750 ml", 22000),
        FakeProduct("MARI MALAKO 1000 ml", 28500),
    ]
    mock_all.return_value.order_by.return_value = products
    service = ProductSearchService()
    hint = normalize_image_hint(
        {
            "confidence": "high",
            "brand": "МариМолоко",
            "product_name": "сгущенка",
            "weight_grams": "750",
            "visible_text": "МариМолоко сгущенка 750",
            "search_queries": [],
        }
    )
    result = service.search_from_image_hint(hint)
    assert len(result.matches) == 1
    assert result.matches[0].product.product_name == "MARI MALAKO 750 ml"


@patch("shop.services.product_search.Product.objects.all")
def test_image_search_returns_single_exact_match(mock_all):
    products = [
        _product("Bonduelle yashil noxat 425g", 15000, category="konserva"),
        _product("Bonduelle qizil lobya 425g", 14000, category="konserva"),
        _product("Ansor tushonka", 10000, category="tushonka"),
    ]
    mock_all.return_value.order_by.return_value = products
    service = ProductSearchService()
    hint = {
        "confidence": "high",
        "brand": "Bonduelle",
        "product_name": "yashil noxat",
        "weight_grams": "425",
        "search_queries": ["bonduelle yashil noxat 425"],
    }
    result = service.search_from_image_hint(hint)
    assert len(result.matches) == 1
    assert "yashil noxat" in result.matches[0].product.product_name.lower()


@patch("shop.services.product_search.Product.objects.all")
def test_image_search_rejects_category_only_match(mock_all):
    products = [
        _product("Ansor tushonka", 10000, category="tushonka"),
        _product("Poyqadam tushonka", 12000, category="tushonka"),
        _product("Halol tushonka", 11000, category="tushonka"),
    ]
    mock_all.return_value.order_by.return_value = products
    service = ProductSearchService()
    hint = {
        "confidence": "medium",
        "brand": "ansor",
        "product_name": "tushonka",
        "search_queries": ["tushonka"],
    }
    result = service.search_from_image_hint(hint)
    assert result.matches == []
