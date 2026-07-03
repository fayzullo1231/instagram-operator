from unittest.mock import MagicMock, patch

from django.test import override_settings

from shop.services.kuloloptom_client import KulolOptomClient


def test_kuloloptom_parse_product_uses_name_and_price():
    parsed = KulolOptomClient.parse_product(
        {
            "id": "abc-123",
            "name": "Asra Schoko Zeit 350g",
            "price": "25000.00",
            "quantity": "12.000",
            "category_name": "Shokolad",
            "brand_name": "Asra",
            "barcodes": ["8600123456789"],
            "is_active": True,
        }
    )
    assert parsed["product_name"] == "Asra Schoko Zeit 350g"
    assert parsed["price"] == 25000.0
    assert parsed["source"] == "kuloloptom"
    assert parsed["external_id"] == "abc-123"


@override_settings(
    KULOLOPTOM_ENABLED=True,
    TEZPOS_API_URL="http://127.0.0.1:8000",
    KULOLOPTOM_SERVER_NAME="kuloloptom-2",
    KULOLOPTOM_API_TOKEN="",
    KULOLOPTOM_LOGIN="",
    KULOLOPTOM_PASSWORD="",
)
def test_kuloloptom_configured_without_token():
    client = KulolOptomClient()
    assert client.is_configured is True
    assert client.has_auth_credentials is False


@override_settings(
    KULOLOPTOM_ENABLED=True,
    TEZPOS_API_URL="http://127.0.0.1:8000",
    KULOLOPTOM_SERVER_NAME="kuloloptom-2",
    KULOLOPTOM_API_TOKEN="test-token-123",
    KULOLOPTOM_LOGIN="",
    KULOLOPTOM_PASSWORD="",
)
@patch("shop.services.kuloloptom_client.httpx.Client")
def test_kuloloptom_fetch_uses_api_token_without_login(mock_client_cls):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [{"id": "1", "name": "Test", "price": "1000", "is_active": True}]

    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.get.return_value = mock_response
    mock_client_cls.return_value = mock_client

    products = KulolOptomClient().fetch_all_products()

    assert len(products) == 1
    headers = mock_client.get.call_args.kwargs["headers"]
    assert headers["Authorization"] == "Token test-token-123"
    assert headers["X-Server-Name"] == "kuloloptom-2"
    mock_client.post.assert_not_called()


@override_settings(
    KULOLOPTOM_ENABLED=True,
    TEZPOS_API_URL="http://127.0.0.1:8000",
    KULOLOPTOM_SERVER_NAME="kuloloptom-2",
    KULOLOPTOM_API_TOKEN="",
    KULOLOPTOM_LOGIN="",
    KULOLOPTOM_PASSWORD="",
)
@patch("shop.services.kuloloptom_client.httpx.Client")
def test_kuloloptom_fetch_public_without_auth(mock_client_cls):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [{"id": "1", "name": "Test", "price": "1000", "is_active": True}]

    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.get.return_value = mock_response
    mock_client_cls.return_value = mock_client

    products = KulolOptomClient().fetch_all_products()

    assert len(products) == 1
    mock_client.get.assert_called_once()
    assert mock_client.get.call_args.kwargs.get("headers") is None
