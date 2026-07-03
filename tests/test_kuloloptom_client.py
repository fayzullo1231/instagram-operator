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
