from unittest.mock import MagicMock, patch

from shop.services.product_search import SearchMatch, SearchResult
from shop.services.text_catalog_matcher import TextCatalogMatcherService
from tests.test_search import FakeProduct


def _match(name: str, price: float = 10000, *, match_type: str = "fuzzy", score: float = 70.0):
    return SearchMatch(product=FakeProduct(name, price), score=score, match_type=match_type)


@patch("shop.services.text_catalog_matcher.OpenAI")
def test_suggest_queries_returns_corrected_terms(mock_openai):
    mock_client = MagicMock()
    mock_openai.return_value = mock_client
    mock_client.chat.completions.create.return_value.choices = [
        MagicMock(
            message=MagicMock(
                content='{"search_queries": ["president", "prezident"], "skip": false}'
            )
        )
    ]

    service = TextCatalogMatcherService(mock_client)
    queries = service.suggest_queries("prizdent qancha", tried=["prizdent"])

    assert "president" in queries
    assert "prezident" in queries


@patch("shop.services.text_catalog_matcher.OpenAI")
def test_filter_matches_rejects_when_not_confident(mock_openai):
    mock_client = MagicMock()
    mock_openai.return_value = mock_client
    mock_client.chat.completions.create.return_value.choices = [
        MagicMock(message=MagicMock(content='{"product_ids": [], "confident": false}'))
    ]

    service = TextCatalogMatcherService(mock_client)
    result = service.filter_matches(
        "prizdent",
        [_match("ALSAFI SIR 400 gr"), _match("Antica Makaron 400gr")],
    )

    assert result.matches == []


@patch("shop.services.text_catalog_matcher.OpenAI")
def test_filter_matches_accepts_valid_products(mock_openai):
    president = _match("President sut 400gr", match_type="fuzzy", score=67.0)
    wrong = _match("ALSAFI SIR 400 gr", match_type="fuzzy", score=66.0)
    mock_client = MagicMock()
    mock_openai.return_value = mock_client
    mock_client.chat.completions.create.return_value.choices = [
        MagicMock(
            message=MagicMock(
                content=(
                    f'{{"product_ids": [{president.product.id}], "confident": true}}'
                )
            )
        )
    ]

    service = TextCatalogMatcherService(mock_client)
    result = service.filter_matches("prizdent", [wrong, president])

    assert len(result.matches) == 1
    assert result.matches[0].product.product_name == "President sut 400gr"


def test_is_trusted_result_rejects_low_fuzzy_score():
    from shop.services.product_search import ProductSearchService

    result = SearchResult(
        matches=[_match("President sut 400gr", score=67.0, match_type="fuzzy")]
    )
    assert ProductSearchService.is_trusted_result(result) is False

    trusted = SearchResult(
        matches=[_match("President sut 400gr", score=85.0, match_type="fuzzy")]
    )
    assert ProductSearchService.is_trusted_result(trusted) is True
