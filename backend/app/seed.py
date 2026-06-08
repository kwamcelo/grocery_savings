import argparse
import re
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .db import Base, SessionLocal, engine
from .models import NormalizedProduct, ProductAlias, Receipt, ReceiptItem, Store


PRODUCTS = [
    {
        "name": "Mexican Mango",
        "category": "Produce",
        "aliases": ["mango mx", "mex mango", "mangos", "mango mexican", "mexican mango"],
    },
    {
        "name": "Bananas",
        "category": "Produce",
        "aliases": ["banana", "bananas", "bnna", "organic bananas"],
    },
    {
        "name": "Milk",
        "category": "Dairy",
        "aliases": ["milk", "milk 2l", "2 percent milk", "whole milk"],
    },
    {
        "name": "Eggs",
        "category": "Dairy",
        "aliases": ["eggs", "eggs dozen", "large eggs", "dozen eggs"],
    },
    {
        "name": "Spinach",
        "category": "Produce",
        "aliases": ["spinach", "baby spinach", "spinach org"],
    },
]

RECEIPTS = [
    {
        "store": "Fresh Market",
        "purchased_at": date(2026, 6, 1),
        "raw_text": "Fresh Market\n2026-06-01\nMANGO MX 2.99\nMilk 2L 5.49\nEggs dozen 4.79",
        "items": [
            ("MANGO MX", "Mexican Mango", 1.0, "ct", 2.99),
            ("Milk 2L", "Milk", 2.0, "l", 5.49),
            ("Eggs dozen", "Eggs", 12.0, "ct", 4.79),
        ],
    },
    {
        "store": "Save-On Foods",
        "purchased_at": date(2026, 6, 3),
        "raw_text": "Save-On Foods\n2026-06-03\nMEX MANGO 3.49\nBANANAS 1.24\nBABY SPINACH 3.99",
        "items": [
            ("MEX MANGO", "Mexican Mango", 1.0, "ct", 3.49),
            ("BANANAS", "Bananas", 1.0, "lb", 1.24),
            ("BABY SPINACH", "Spinach", 1.0, "ct", 3.99),
        ],
    },
    {
        "store": "No Frills",
        "purchased_at": date(2026, 6, 5),
        "raw_text": "No Frills\n2026-06-05\nMANGOS 2.49\nBNNA 0.89\n2 PERCENT MILK 4.99",
        "items": [
            ("MANGOS", "Mexican Mango", 1.0, "ct", 2.49),
            ("BNNA", "Bananas", 1.0, "lb", 0.89),
            ("2 PERCENT MILK", "Milk", 2.0, "l", 4.99),
        ],
    },
]


def reset_database() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def create_tables() -> None:
    Base.metadata.create_all(bind=engine)


def seed_database() -> None:
    with SessionLocal() as db:
        product_by_name = seed_products(db)
        seed_receipts(db, product_by_name)
        db.commit()


def seed_products(db: Session) -> dict[str, NormalizedProduct]:
    product_by_name: dict[str, NormalizedProduct] = {}

    for product_data in PRODUCTS:
        product = db.scalar(
            select(NormalizedProduct).where(
                func.lower(NormalizedProduct.name) == product_data["name"].lower()
            )
        )
        if not product:
            product = NormalizedProduct(
                name=product_data["name"],
                category=product_data["category"],
            )
            db.add(product)
            db.flush()

        product_by_name[product.name] = product

        for alias in product_data["aliases"]:
            canonical = canonical_alias(alias)
            exists = db.scalar(select(ProductAlias).where(ProductAlias.alias == canonical))
            if not exists:
                db.add(ProductAlias(normalized_product_id=product.id, alias=canonical))

    db.flush()
    return product_by_name


def seed_receipts(
    db: Session,
    product_by_name: dict[str, NormalizedProduct],
) -> None:
    for receipt_data in RECEIPTS:
        store = get_or_create_store(db, receipt_data["store"])
        existing = db.scalar(
            select(Receipt).where(
                Receipt.store_id == store.id,
                Receipt.purchased_at == receipt_data["purchased_at"],
                Receipt.raw_text == receipt_data["raw_text"],
            )
        )
        if existing:
            continue

        receipt = Receipt(
            store_id=store.id,
            purchased_at=receipt_data["purchased_at"],
            original_filename="seed-receipt.txt",
            raw_text=receipt_data["raw_text"],
        )
        db.add(receipt)
        db.flush()

        for raw_name, product_name, quantity, unit, price in receipt_data["items"]:
            product = product_by_name[product_name]
            db.add(
                ReceiptItem(
                    receipt_id=receipt.id,
                    store_id=store.id,
                    normalized_product_id=product.id,
                    raw_item_name=raw_name,
                    quantity=quantity,
                    unit=unit,
                    price=price,
                    purchased_at=receipt.purchased_at,
                )
            )


def get_or_create_store(db: Session, name: str) -> Store:
    store = db.scalar(select(Store).where(func.lower(Store.name) == name.lower()))
    if store:
        return store

    store = Store(name=name)
    db.add(store)
    db.flush()
    return store


def canonical_alias(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def main() -> None:
    parser = argparse.ArgumentParser(description="Create and seed the local grocery database.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop all tables before recreating and seeding. Use only for local development.",
    )
    args = parser.parse_args()

    if args.reset:
        reset_database()
    else:
        create_tables()
    seed_database()
    print("Seeded grocery tracker database.")


if __name__ == "__main__":
    main()
