import json
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.services.parser import ParsedItem, ParsedReceipt
from app.models import NormalizedProduct, ProductAlias, Receipt, ReceiptItem, Store


def create_product_fixture(db: Session) -> NormalizedProduct:
    product = NormalizedProduct(name="Mexican Mango", category="Produce")
    db.add(product)
    db.flush()
    db.add_all(
        [
            ProductAlias(normalized_product_id=product.id, alias="mango mx"),
            ProductAlias(normalized_product_id=product.id, alias="mex mango"),
            ProductAlias(normalized_product_id=product.id, alias="mangos"),
        ]
    )
    db.commit()
    return product


def create_purchase(
    db: Session,
    product: NormalizedProduct,
    store_name: str,
    raw_name: str,
    price: float,
    quantity: float | None,
    unit: str | None,
    purchased_at: date,
    unit_price: float | None = None,
    unit_price_unit: str | None = None,
) -> None:
    store = Store(name=store_name)
    db.add(store)
    db.flush()
    receipt = Receipt(
        store_id=store.id,
        purchased_at=purchased_at,
        raw_text=f"{store_name}\n{raw_name} {price}",
    )
    db.add(receipt)
    db.flush()
    db.add(
        ReceiptItem(
            receipt_id=receipt.id,
            store_id=store.id,
            normalized_product_id=product.id,
            raw_item_name=raw_name,
            price=price,
            quantity=quantity,
            unit=unit,
            unit_price=unit_price,
            unit_price_unit=unit_price_unit,
            purchased_at=purchased_at,
        )
    )
    db.commit()


def test_save_receipt_persists_corrected_items(client: TestClient) -> None:
    response = client.post(
        "/receipts",
        json={
            "store_name": "Demo Market",
            "store_location_text": "100 Test St Vancouver BC",
            "purchased_at": "2026-06-08",
            "raw_text": "Demo Market\nMilk 2L 4.99",
            "items": [
                {
                    "name": "Milk",
                    "quantity": "2",
                    "unit": "l",
                    "price": 4.99,
                    "source_line": "Milk 2L 4.99",
                    "normalized_product_id": None,
                    "reject_normalization_suggestion": False,
                }
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["store_name"] == "Demo Market"
    assert body["items"][0]["raw_item_name"] == "Milk"
    assert body["items"][0]["quantity"] == 2.0
    assert body["items"][0]["unit"] == "l"
    assert body["items"][0]["unit_price"] is None
    assert body["items"][0]["unit_price_unit"] is None


def test_product_search_matches_aliases_and_raw_names(
    client: TestClient,
    db_session: Session,
) -> None:
    product = create_product_fixture(db_session)
    create_purchase(
        db_session,
        product,
        "Fresh Market",
        "MANGO MX",
        2.99,
        1,
        "ct",
        date(2026, 6, 1),
    )

    response = client.get("/products/search", params={"q": "Mexican mangos"})

    assert response.status_code == 200
    body = response.json()
    assert body[0]["name"] == "Mexican Mango"
    assert "MANGO MX" in body[0]["matched_raw_item_names"]


def test_compare_prices_prefers_receipt_unit_price_when_available(
    client: TestClient,
    db_session: Session,
) -> None:
    product = NormalizedProduct(name="Milk", category="Dairy")
    db_session.add(product)
    db_session.flush()
    db_session.add(ProductAlias(normalized_product_id=product.id, alias="milk"))
    db_session.commit()

    create_purchase(
        db_session,
        product,
        "Store A",
        "Milk 2L",
        5.00,
        2,
        "l",
        date(2026, 6, 1),
        unit_price=2.25,
        unit_price_unit="l",
    )
    create_purchase(db_session, product, "Store B", "Milk 1L", 3.00, 1, "l", date(2026, 6, 2))

    response = client.get("/items/compare", params={"name": "milk"})

    assert response.status_code == 200
    body = response.json()
    assert body["by_store"][0]["store_name"] == "Store A"
    assert body["by_store"][0]["lowest_unit_price"] == 2.25
    assert body["by_store"][0]["comparison_reliable"] is True
    assert body["matches"][0]["source_unit_price"] == 2.25
    assert body["matches"][0]["source_unit_price_unit"] == "l"


def test_compare_prices_flags_missing_units(
    client: TestClient,
    db_session: Session,
) -> None:
    product = NormalizedProduct(name="Spinach", category="Produce")
    db_session.add(product)
    db_session.flush()
    db_session.add(ProductAlias(normalized_product_id=product.id, alias="spinach"))
    db_session.commit()

    create_purchase(db_session, product, "Store A", "Spinach", 3.29, None, None, date(2026, 6, 1))

    response = client.get("/items/compare", params={"name": "spinach"})

    assert response.status_code == 200
    body = response.json()
    assert body["by_store"][0]["comparison_reliable"] is False
    assert "Missing quantity or unit" in body["by_store"][0]["comparison_warning"]


def test_receipt_image_fixtures_are_uploadable_when_present(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    receipt_dir = Path(__file__).resolve().parents[1] / "test_receipts"
    image_paths = [
        path
        for path in receipt_dir.glob("*")
        if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}
    ]
    if not image_paths:
        pytest.skip("No image receipts found in backend/test_receipts.")

    def fake_extract_receipt_from_image(image_bytes: bytes, mime_type: str | None = None):
        parsed = ParsedReceipt(
            store_name="Demo Market",
            store_location_text="100 Test St Vancouver BC",
            purchased_at=None,
            items=[
                ParsedItem(
                    line="Milk 2L 4.99",
                    name="Milk",
                    quantity="2",
                    unit="l",
                    unit_price=None,
                    unit_price_unit=None,
                    price=4.99,
                )
            ],
        )
        return "Demo Market\nMilk 2L 4.99", parsed

    monkeypatch.setattr("app.main.extract_receipt_from_image", fake_extract_receipt_from_image)

    image_path = image_paths[0]
    response = client.post(
        "/receipts/upload",
        files={"file": (image_path.name, image_path.read_bytes(), "image/png")},
    )

    assert response.status_code == 200
    assert response.json()["extracted_text"]


def test_img_4255_expected_payload_saves_explicit_unit_prices(client: TestClient) -> None:
    expected_path = Path(__file__).resolve().parents[1] / "test_receipts" / "IMG_4255_expected.json"
    payload = json.loads(expected_path.read_text())

    response = client.post("/receipts", json=payload)

    assert response.status_code == 200
    body = response.json()
    sweet_potato = next(item for item in body["items"] if item["raw_item_name"] == "Sweet Potato")
    assert sweet_potato["quantity"] == 1.81
    assert sweet_potato["unit"] == "lb"
    assert sweet_potato["unit_price"] == 1.99
    assert sweet_potato["unit_price_unit"] == "lb"
