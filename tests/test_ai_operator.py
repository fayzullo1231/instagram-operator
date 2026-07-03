from unittest.mock import MagicMock, patch

from shop.services.ai_operator import AIOperatorService
from shop.services.operator_prompts import NOT_FOUND_REPLY


@patch("shop.services.ai_operator.ProductSearchService")
@patch("shop.services.ai_operator.OpenAI")
def test_greeting_uses_chatgpt(mock_openai, mock_search_cls):
    mock_client = MagicMock()
    mock_openai.return_value = mock_client
    mock_client.chat.completions.create.return_value.choices = [
        MagicMock(message=MagicMock(content="Assalomu alaykum! Qanday yordam bera olaman?"))
    ]

    service = AIOperatorService()
    response = service.process_message("Assalomu alaykum qalaysiz")

    assert "katalogimizda topilmadi" not in response.reply.lower()
    assert mock_client.chat.completions.create.called


@patch("shop.services.ai_operator.ProductSearchService")
@patch("shop.services.ai_operator.OpenAI")
def test_general_question_without_catalog_match_uses_chatgpt(mock_openai, mock_search_cls):
    mock_client = MagicMock()
    mock_openai.return_value = mock_client
    mock_client.chat.completions.create.return_value.choices = [
        MagicMock(message=MagicMock(content="Bizda oziq-ovqat mahsulotlari bor."))
    ]

    mock_search = mock_search_cls.return_value
    mock_search.search.return_value.matches = []
    mock_search.is_single_match.return_value = False

    service = AIOperatorService()
    response = service.process_message("Sizda qanday mahsulotlar bor?")

    assert response.reply != NOT_FOUND_REPLY
    assert mock_client.chat.completions.create.called


@patch("shop.services.ai_operator.ProductSearchService")
@patch("shop.services.ai_operator.OpenAI")
def test_clear_product_miss_uses_admin_handoff(mock_openai, mock_search_cls):
    mock_client = MagicMock()
    mock_openai.return_value = mock_client
    mock_client.chat.completions.create.side_effect = [
        MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(
                        content='{"intent":"product","search_query":"xyz maxsus mahsulot","category":""}'
                    )
                )
            ]
        ),
        MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(
                        content="Adminlarimiz tez orada tekshirib javob berishadi."
                    )
                )
            ]
        ),
    ]

    mock_search = mock_search_cls.return_value
    mock_search.search.return_value.matches = []
    mock_search.is_single_match.return_value = False

    service = AIOperatorService()
    response = service.process_message("xyz maxsus mahsulot bormi")

    assert "katalogimizda topilmadi" not in response.reply.lower()
    assert "admin" in response.reply.lower()
