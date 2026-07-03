from unittest.mock import MagicMock, patch

from shop.models import Product
from shop.services.ai_operator import AIOperatorService
from shop.services.catalog_matcher import CatalogMatcherService
from shop.services.product_search import SearchMatch, SearchResult


@patch("shop.services.ai_operator.ProductSearchService")
@patch("shop.services.ai_operator.OpenAI")
@patch("shop.services.ai_operator.fetch_image_as_data_url")
def test_image_no_match_returns_empty_reply(mock_data_url, mock_openai, mock_search_cls):
    mock_data_url.return_value = "data:image/jpeg;base64,abc"
    mock_client = MagicMock()
    mock_openai.return_value = mock_client
    mock_client.chat.completions.create.return_value.choices = [
        MagicMock(
            message=MagicMock(
                content=(
                    '{"confidence":"high","brand":"Test","product_name":"xyz",'
                    '"identified_product":"Test xyz 1kg","catalog_search_query":"test xyz",'
                    '"search_queries":["test xyz"]}'
                )
            )
        )
    ]

    mock_search = mock_search_cls.return_value
    mock_search.search_from_image_hint.return_value = SearchResult(matches=[])

    with patch.object(CatalogMatcherService, "match_with_ai", return_value=SearchResult(matches=[])), patch.object(
        CatalogMatcherService, "match_by_fuzzy", return_value=SearchResult(matches=[])
    ):
        service = AIOperatorService()
        response = service.process_message("rasm", image_url="http://example.com/a.jpg")

    assert response.reply == ""
    assert "topilmadi" not in response.reply.lower()


@patch("shop.services.ai_operator.ProductSearchService")
@patch("shop.services.ai_operator.OpenAI")
@patch("shop.services.ai_operator.fetch_image_as_data_url")
def test_image_match_returns_catalog_name_and_price(mock_data_url, mock_openai, mock_search_cls):
    mock_data_url.return_value = "data:image/jpeg;base64,abc"
    mock_client = MagicMock()
    mock_openai.return_value = mock_client
    mock_client.chat.completions.create.return_value.choices = [
        MagicMock(
            message=MagicMock(
                content=(
                    '{"confidence":"high","brand":"Asra","product_name":"shokolad",'
                    '"identified_product":"Asra Schoko 350g","catalog_search_query":"asra 350",'
                    '"search_queries":["asra 350"]}'
                )
            )
        )
    ]

    product = Product(
        id=1,
        external_id="1",
        product_name="Asra Schoko Zeit 350g",
        price=25000,
        source="kuloloptom",
    )
    match = SearchMatch(product=product, score=92.0, match_type="fuzzy_image")

    mock_search = mock_search_cls.return_value
    mock_search.search_from_image_hint.return_value = SearchResult(matches=[])
    mock_search.is_single_match.return_value = True

    with patch.object(CatalogMatcherService, "match_with_ai", return_value=SearchResult(matches=[])), patch.object(
        CatalogMatcherService, "match_by_fuzzy", return_value=SearchResult(matches=[match])
    ):
        service = AIOperatorService()
        response = service.process_message("rasm", image_url="http://example.com/a.jpg")

    assert "Asra Schoko Zeit 350g" in response.reply
    assert "25 000 so'm" in response.reply
    assert "topilmadi" not in response.reply.lower()
