from app.services.parser import parse_receipt_text


def test_parse_receipt_text_extracts_store_location_date_and_items() -> None:
    parsed = parse_receipt_text(
        "\n".join(
            [
                "Fresh Market",
                "123 Main St Vancouver BC V6B 1A1",
                "2026-06-01",
                "MANGO MX 2.99",
                "Milk 2L 5.49",
                "Subtotal 8.48",
            ]
        )
    )

    assert parsed.store_name == "Fresh Market"
    assert parsed.store_location_text == "123 Main St Vancouver BC V6B 1A1"
    assert parsed.purchased_at.isoformat() == "2026-06-01"
    assert [(item.name, item.price) for item in parsed.items] == [
        ("Mango Mx", 2.99),
        ("Milk 2L", 5.49),
    ]
    assert parsed.items[1].quantity == "2"
    assert parsed.items[1].unit == "l"


def test_parse_receipt_text_extracts_receipt_unit_price() -> None:
    parsed = parse_receipt_text(
        "\n".join(
            [
                "Kim's MART",
                "519 E Broadway Vancouver BC V5T1X4",
                "2026-05-19",
                "Sweet Potato 1.81 lb @ $1.99/lb 3.60",
                "Lemon 3 @ $0.69 1.99",
            ]
        )
    )

    assert parsed.items[0].name == "Sweet Potato"
    assert parsed.items[0].quantity == "1.81"
    assert parsed.items[0].unit == "lb"
    assert parsed.items[0].unit_price == 1.99
    assert parsed.items[0].unit_price_unit == "lb"
    assert parsed.items[0].price == 3.60

    assert parsed.items[1].name == "Lemon"
    assert parsed.items[1].quantity == "3"
    assert parsed.items[1].unit == "ct"
    assert parsed.items[1].unit_price == 0.69
    assert parsed.items[1].unit_price_unit == "ct"
