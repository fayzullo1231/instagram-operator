from unittest.mock import MagicMock, patch

from shop.services.product_sync import ProductSyncService


@patch("shop.services.product_sync.TezPOSClient")
@patch("shop.services.product_sync.KulolOptomClient")
@patch("shop.services.product_sync.MDoKonClient")
@patch("shop.services.product_sync.LinkoClient")
def test_sync_skips_tezpos_when_kuloloptom_enabled(mock_linko, mock_mdokon, mock_kulol, mock_tezpos):
    mock_linko.return_value.fetch_all_products.return_value = []
    mock_mdokon.return_value.is_configured = False
    mock_kulol.return_value.is_configured = True
    mock_kulol.return_value.fetch_all_products.return_value = []
    mock_tezpos.return_value.is_configured = True

    with patch.object(ProductSyncService, "_upsert_products", return_value=0):
        ProductSyncService().sync_all()

    mock_tezpos.return_value.fetch_all_products.assert_not_called()


@patch("shop.services.product_sync.KulolOptomClient")
@patch("shop.services.product_sync.MDoKonClient")
@patch("shop.services.product_sync.LinkoClient")
@patch("shop.services.product_sync.TezPOSClient")
def test_sync_continues_when_one_source_fails(mock_tezpos, mock_linko, mock_mdokon, mock_kulol):
    mock_linko.return_value.fetch_all_products.side_effect = RuntimeError("linko down")
    mock_mdokon.return_value.is_configured = True
    mock_mdokon.return_value.fetch_all_products.return_value = [
        {"productId": "1", "productName": "Test", "salePrice": 1000, "balance": 1}
    ]
    mock_mdokon.return_value.parse_product.return_value = {
        "external_id": "1",
        "product_name": "Test",
        "price": 1000.0,
        "balance": 1.0,
        "source": "mdokon",
    }
    mock_tezpos.return_value.is_configured = False
    mock_kulol.return_value.is_configured = False

    with patch.object(ProductSyncService, "_upsert_products", return_value=1):
        result = ProductSyncService().sync_all()

    assert result["mdokon_count"] == 1
    assert "linko" in result["errors"]
