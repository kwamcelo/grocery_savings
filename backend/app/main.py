import re

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from .db import Base, engine, get_db
from .models import (
    NormalizedProduct,
    ProductAlias,
    Receipt,
    ReceiptItem,
    Store,
)
from .schemas import (
    CompareResult,
    NormalizedProductRead,
    ReceiptRead,
    SearchResult,
    StorePriceSummary,
    StoreRead,
)
from .services.ocr import extract_text_from_image
from .services.parser import parse_receipt_text


app = FastAPI(title="Grocery Receipt Price Tracker API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/stores", response_model=list[StoreRead])
def list_stores(db: Session = Depends(get_db)) -> list[Store]:
    return list(db.scalars(select(Store).order_by(Store.name.asc())))


@app.get("/products", response_model=list[NormalizedProductRead])
def list_products(db: Session = Depends(get_db)) -> list[NormalizedProduct]:
    return list(
        db.scalars(
            select(NormalizedProduct)
            .options(selectinload(NormalizedProduct.aliases))
            .order_by(NormalizedProduct.name.asc())
        )
    )


@app.post("/receipts/upload", response_model=ReceiptRead)
async def upload_receipt(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> Receipt:
    if file.content_type and not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Please upload an image file.")

    image_bytes = await file.read()
    raw_text = extract_text_from_image(image_bytes)
    parsed = parse_receipt_text(raw_text)
    store = get_or_create_store(db, parsed.store_name)

    receipt = Receipt(
        store_id=store.id,
        purchased_at=parsed.purchased_at,
        original_filename=file.filename,
        raw_text=raw_text,
    )
    db.add(receipt)
    db.flush()

    receipt.items = [
        ReceiptItem(
            receipt_id=receipt.id,
            store_id=store.id,
            normalized_product_id=get_or_create_product_for_raw_item(db, item.name).id,
            raw_item_name=item.name,
            price=item.price,
            quantity=parse_quantity(item.quantity)[0],
            unit=parse_quantity(item.quantity)[1],
            purchased_at=parsed.purchased_at,
        )
        for item in parsed.items
    ]

    db.commit()
    return load_receipt(db, receipt.id)


@app.get("/receipts", response_model=list[ReceiptRead])
def list_receipts(db: Session = Depends(get_db)) -> list[Receipt]:
    return list(
        db.scalars(
            select(Receipt)
            .options(
                selectinload(Receipt.store),
                selectinload(Receipt.items).selectinload(ReceiptItem.normalized_product),
            )
            .order_by(Receipt.created_at.desc())
        )
    )


@app.get("/items/search", response_model=list[SearchResult])
def search_items(q: str, db: Session = Depends(get_db)) -> list[SearchResult]:
    product_ids = matching_product_ids(db, q)
    filters = [
        ReceiptItem.raw_item_name.ilike(f"%{q}%"),
        NormalizedProduct.name.ilike(f"%{q}%"),
    ]
    if product_ids:
        filters.append(ReceiptItem.normalized_product_id.in_(product_ids))

    rows = db.execute(
        select(ReceiptItem, Store)
        .join(Store, ReceiptItem.store_id == Store.id)
        .outerjoin(
            NormalizedProduct,
            ReceiptItem.normalized_product_id == NormalizedProduct.id,
        )
        .where(or_(*filters))
        .order_by(ReceiptItem.purchased_at.desc(), ReceiptItem.price.asc())
    ).all()
    return [to_search_result(item, store) for item, store in rows]


@app.get("/items/compare", response_model=CompareResult)
def compare_items(name: str, db: Session = Depends(get_db)) -> CompareResult:
    product_ids = matching_product_ids(db, name)
    filters = [
        ReceiptItem.raw_item_name.ilike(f"%{name}%"),
        NormalizedProduct.name.ilike(f"%{name}%"),
    ]
    if product_ids:
        filters.append(ReceiptItem.normalized_product_id.in_(product_ids))

    rows = db.execute(
        select(ReceiptItem, Store)
        .join(Store, ReceiptItem.store_id == Store.id)
        .outerjoin(
            NormalizedProduct,
            ReceiptItem.normalized_product_id == NormalizedProduct.id,
        )
        .where(or_(*filters))
        .order_by(ReceiptItem.price.asc())
    ).all()

    summaries = db.execute(
        select(
            Store.name,
            func.min(ReceiptItem.price),
            func.max(ReceiptItem.price),
            func.avg(ReceiptItem.price),
            func.count(ReceiptItem.id),
        )
        .select_from(ReceiptItem)
        .join(Store, ReceiptItem.store_id == Store.id)
        .outerjoin(
            NormalizedProduct,
            ReceiptItem.normalized_product_id == NormalizedProduct.id,
        )
        .where(or_(*filters))
        .group_by(Store.name)
        .order_by(func.avg(ReceiptItem.price).asc())
    ).all()

    return CompareResult(
        query=name,
        matches=[to_search_result(item, store) for item, store in rows],
        by_store=[
            StorePriceSummary(
                store_name=store,
                lowest_price=round(low, 2),
                highest_price=round(high, 2),
                average_price=round(avg, 2),
                observations=count,
            )
            for store, low, high, avg, count in summaries
        ],
    )


def load_receipt(db: Session, receipt_id: int) -> Receipt:
    receipt = db.scalar(
        select(Receipt)
        .options(
            selectinload(Receipt.store),
            selectinload(Receipt.items).selectinload(ReceiptItem.normalized_product),
        )
        .where(Receipt.id == receipt_id)
    )
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")
    return receipt


def get_or_create_store(db: Session, name: str) -> Store:
    store_name = " ".join(name.split()).strip() or "Unknown Store"
    store = db.scalar(select(Store).where(func.lower(Store.name) == store_name.lower()))
    if store:
        return store

    store = Store(name=store_name)
    db.add(store)
    db.flush()
    return store


def get_or_create_product_for_raw_item(db: Session, raw_item_name: str) -> NormalizedProduct:
    alias = canonical_alias(raw_item_name)
    product = db.scalar(
        select(NormalizedProduct)
        .join(ProductAlias)
        .where(ProductAlias.alias == alias)
    )
    if product:
        return product

    product_name = normalize_product_name(raw_item_name)
    product = db.scalar(
        select(NormalizedProduct).where(func.lower(NormalizedProduct.name) == product_name.lower())
    )
    if not product:
        product = NormalizedProduct(name=product_name)
        db.add(product)
        db.flush()

    db.add(ProductAlias(normalized_product_id=product.id, alias=alias))
    db.flush()
    return product


def matching_product_ids(db: Session, query: str) -> list[int]:
    canonical = canonical_alias(query)
    return list(
        db.scalars(
            select(ProductAlias.normalized_product_id).where(
                or_(
                    ProductAlias.alias.ilike(f"%{canonical}%"),
                    ProductAlias.alias.ilike(f"%{query.lower()}%"),
                )
            )
        )
    )


def parse_quantity(quantity_text: str | None) -> tuple[float | None, str | None]:
    if not quantity_text:
        return None, None
    match = re.match(r"(?P<quantity>\d+(?:\.\d+)?)\s?(?P<unit>[a-zA-Z]+)?", quantity_text)
    if not match:
        return None, quantity_text
    unit = match.group("unit")
    return float(match.group("quantity")), unit.lower() if unit else None


def normalize_product_name(raw_item_name: str) -> str:
    cleaned = re.sub(r"\b\d+(?:\.\d+)?\s?(?:kg|g|lb|lbs|oz|l|ml|ct|x)\b", "", raw_item_name, flags=re.I)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned.title() or raw_item_name.title()


def canonical_alias(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def to_search_result(item: ReceiptItem, store: Store) -> SearchResult:
    return SearchResult(
        item_id=item.id,
        raw_item_name=item.raw_item_name,
        name=item.name,
        normalized_product_name=item.normalized_product_name,
        quantity=item.quantity,
        unit=item.unit,
        price=item.price,
        store_id=store.id,
        store_name=store.name,
        purchased_at=item.purchased_at,
        receipt_id=item.receipt_id,
    )
