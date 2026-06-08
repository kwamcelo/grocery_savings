import re
from datetime import date
from difflib import SequenceMatcher
from typing import NamedTuple

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from .db import Base, engine, get_db
from .migrations import run_lightweight_migrations
from .models import (
    NormalizedProduct,
    ProductAlias,
    Receipt,
    ReceiptItem,
    Store,
)
from .schemas import (
    CompareResult,
    NormalizationSuggestionRead,
    NormalizedProductRead,
    ParsedReceiptRead,
    ProductPriceHistory,
    ProductPurchaseRecord,
    ProductSearchCandidate,
    ProductStorePriceGroup,
    ReceiptPreviewResponse,
    ReceiptRead,
    SaveReceiptRequest,
    SearchResult,
    StorePriceSummary,
    StoreRead,
)
from .services.ocr import extract_text_from_image
from .services.parser import parse_receipt_text
from .services.storage import save_upload


app = FastAPI(title="Grocery Receipt Price Tracker API")
AUTO_NORMALIZATION_THRESHOLD = 0.94
REVIEW_NORMALIZATION_THRESHOLD = 0.58


class ProductMatch(NamedTuple):
    product: NormalizedProduct
    score: float
    matched_on: str
    auto_match: bool

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
    run_lightweight_migrations(engine)


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


@app.get("/products/search", response_model=list[ProductSearchCandidate])
def search_products(q: str, db: Session = Depends(get_db)) -> list[ProductSearchCandidate]:
    query_tokens = query_terms(q)
    if not query_tokens:
        return []

    products = list(
        db.scalars(
            select(NormalizedProduct)
            .options(
                selectinload(NormalizedProduct.aliases),
                selectinload(NormalizedProduct.receipt_items),
            )
            .order_by(NormalizedProduct.name.asc())
        )
    )

    candidates = [
        to_product_candidate(product)
        for product in products
        if product_matches_query(product, query_tokens)
    ]
    return sorted(
        candidates,
        key=lambda candidate: (
            candidate.lowest_observed_price is None,
            candidate.lowest_observed_price or 0,
            candidate.name,
        ),
    )


@app.get("/products/{product_id}/price-history", response_model=ProductPriceHistory)
def get_product_price_history(
    product_id: int,
    db: Session = Depends(get_db),
) -> ProductPriceHistory:
    product = db.scalar(
        select(NormalizedProduct).where(NormalizedProduct.id == product_id)
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    rows = db.execute(
        select(ReceiptItem, Store)
        .join(Store, ReceiptItem.store_id == Store.id)
        .where(ReceiptItem.normalized_product_id == product_id)
    ).all()

    groups: dict[int, tuple[Store, list[ReceiptItem]]] = {}
    for item, store in rows:
        if store.id not in groups:
            groups[store.id] = (store, [])
        groups[store.id][1].append(item)

    store_groups = [
        to_store_price_group(store, items)
        for store, items in groups.values()
        if items
    ]
    store_groups.sort(key=lambda group: (group.lowest_observed_price, group.store_name))

    return ProductPriceHistory(
        product_id=product.id,
        product_name=product.name,
        stores=store_groups,
    )


@app.post("/receipts/upload", response_model=ReceiptPreviewResponse)
async def upload_receipt(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if file.content_type and not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Please upload an image file.")

    image_bytes = await file.read()
    saved_path = save_upload(file, image_bytes)
    raw_text = extract_text_from_image(image_bytes)
    parsed = parse_receipt_text(raw_text)

    return ReceiptPreviewResponse(
        image_path=str(saved_path),
        original_filename=file.filename,
        extracted_text=raw_text,
        parsed=to_parsed_receipt_response(parsed, db),
    )


@app.post("/receipts", response_model=ReceiptRead)
def save_receipt(
    payload: SaveReceiptRequest,
    db: Session = Depends(get_db),
) -> Receipt:
    if not payload.items:
        raise HTTPException(status_code=400, detail="At least one receipt item is required.")

    store = get_or_create_store(
        db,
        payload.store_name,
        location_text=payload.store_location_text,
        phone=payload.store_phone,
    )
    receipt = Receipt(
        store_id=store.id,
        purchased_at=payload.purchased_at,
        original_filename=payload.original_filename,
        image_path=payload.image_path,
        raw_text=payload.raw_text,
    )
    db.add(receipt)
    db.flush()

    receipt_items = []
    for item in payload.items:
        item_name = item.name.strip()
        if not item_name:
            continue
        quantity, inferred_unit = parse_quantity(item.quantity)
        unit = item.unit.strip().lower() if item.unit else inferred_unit
        normalized_product = resolve_normalized_product_for_item(db, item)
        receipt_items.append(
            ReceiptItem(
                receipt_id=receipt.id,
                store_id=store.id,
                normalized_product_id=normalized_product.id,
                raw_item_name=item_name,
                price=item.price,
                quantity=quantity,
                unit=unit,
                purchased_at=payload.purchased_at,
            )
        )

    if not receipt_items:
        raise HTTPException(status_code=400, detail="At least one item name is required.")

    receipt.items = receipt_items

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


def get_or_create_store(
    db: Session,
    name: str,
    location_text: str | None = None,
    phone: str | None = None,
) -> Store:
    store_name = " ".join(name.split()).strip() or "Unknown Store"
    store = db.scalar(select(Store).where(func.lower(Store.name) == store_name.lower()))
    if store:
        if location_text and not store.location_text:
            store.location_text = location_text
        if phone and not store.phone:
            store.phone = phone
        return store

    store = Store(name=store_name, location_text=location_text, phone=phone)
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


def resolve_normalized_product_for_item(db: Session, item) -> NormalizedProduct:
    item_name = item.name.strip()

    if item.normalized_product_id and not item.reject_normalization_suggestion:
        product = db.scalar(
            select(NormalizedProduct).where(
                NormalizedProduct.id == item.normalized_product_id
            )
        )
        if product:
            add_alias_if_missing(db, product.id, item_name)
            return product

    if not item.reject_normalization_suggestion:
        match = find_product_match(db, item_name)
        if match and match.auto_match:
            add_alias_if_missing(db, match.product.id, item_name)
            return match.product

    return get_or_create_unmatched_product(db, item_name)


def get_or_create_unmatched_product(db: Session, raw_item_name: str) -> NormalizedProduct:
    product_name = normalize_product_name(raw_item_name)
    product = db.scalar(
        select(NormalizedProduct).where(func.lower(NormalizedProduct.name) == product_name.lower())
    )
    if not product:
        product = NormalizedProduct(name=product_name)
        db.add(product)
        db.flush()

    add_alias_if_missing(db, product.id, raw_item_name)
    return product


def add_alias_if_missing(db: Session, product_id: int, raw_item_name: str) -> None:
    alias = canonical_alias(raw_item_name)
    if not alias:
        return
    existing = db.scalar(select(ProductAlias).where(ProductAlias.alias == alias))
    if not existing:
        db.add(ProductAlias(normalized_product_id=product_id, alias=alias))
        db.flush()


def find_product_match(db: Session, raw_item_name: str) -> ProductMatch | None:
    raw_alias = canonical_alias(raw_item_name)
    if not raw_alias:
        return None

    products = list(
        db.scalars(
            select(NormalizedProduct)
            .options(selectinload(NormalizedProduct.aliases))
            .order_by(NormalizedProduct.name.asc())
        )
    )
    best: ProductMatch | None = None
    for product in products:
        candidate_strings = [product.name, *[alias.alias for alias in product.aliases]]
        for candidate in candidate_strings:
            score = normalization_score(raw_alias, candidate)
            if not best or score > best.score:
                best = ProductMatch(
                    product=product,
                    score=score,
                    matched_on=candidate,
                    auto_match=score >= AUTO_NORMALIZATION_THRESHOLD,
                )

    if best and best.score >= REVIEW_NORMALIZATION_THRESHOLD:
        return best
    return None


def normalization_score(raw_alias: str, candidate: str) -> float:
    candidate_alias = canonical_alias(candidate)
    if not candidate_alias:
        return 0
    if raw_alias == candidate_alias:
        return 1

    raw_tokens = set(query_terms(raw_alias))
    candidate_tokens = set(query_terms(candidate_alias))
    overlap = len(raw_tokens & candidate_tokens) / max(len(raw_tokens | candidate_tokens), 1)
    sequence = SequenceMatcher(None, raw_alias, candidate_alias).ratio()
    abbreviation_bonus = 0.0
    if raw_tokens and candidate_tokens:
        candidate_initials = "".join(token[0] for token in candidate_tokens if token)
        raw_initials = "".join(token[0] for token in raw_tokens if token)
        if raw_initials and raw_initials in candidate_initials:
            abbreviation_bonus = 0.08

    return min(1.0, max(sequence, overlap) + abbreviation_bonus)


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


def to_product_candidate(product: NormalizedProduct) -> ProductSearchCandidate:
    purchases = list(product.receipt_items)
    sorted_by_recent = sorted(
        purchases,
        key=lambda item: item.purchased_at or date.min,
        reverse=True,
    )
    return ProductSearchCandidate(
        product_id=product.id,
        name=product.name,
        category=product.category,
        aliases=sorted(alias.alias for alias in product.aliases),
        matched_raw_item_names=sorted({item.raw_item_name for item in purchases}),
        lowest_observed_price=round(min((item.price for item in purchases), default=0), 2)
        if purchases
        else None,
        most_recent_observed_price=round(sorted_by_recent[0].price, 2)
        if sorted_by_recent
        else None,
        last_purchased_at=sorted_by_recent[0].purchased_at if sorted_by_recent else None,
    )


def to_store_price_group(store: Store, items: list[ReceiptItem]) -> ProductStorePriceGroup:
    purchases_by_price = sorted(items, key=lambda item: (item.price, item.purchased_at or ""))
    purchases_by_recent = sorted(
        items,
        key=lambda item: item.purchased_at or date.min,
        reverse=True,
    )
    most_recent = purchases_by_recent[0]
    return ProductStorePriceGroup(
        store_id=store.id,
        store_name=store.name,
        lowest_observed_price=round(purchases_by_price[0].price, 2),
        most_recent_observed_price=round(most_recent.price, 2),
        last_purchased_at=most_recent.purchased_at,
        purchases=[
            ProductPurchaseRecord(
                item_id=item.id,
                receipt_id=item.receipt_id,
                raw_item_name=item.raw_item_name,
                price=round(item.price, 2),
                quantity=item.quantity,
                unit=item.unit,
                purchased_at=item.purchased_at,
            )
            for item in purchases_by_price
        ],
    )


def product_matches_query(product: NormalizedProduct, tokens: list[str]) -> bool:
    searchable_parts = [product.name]
    searchable_parts.extend(alias.alias for alias in product.aliases)
    searchable_parts.extend(item.raw_item_name for item in product.receipt_items)
    searchable_text = " ".join(canonical_alias(part) for part in searchable_parts)
    searchable_tokens = set(query_terms(searchable_text))
    return all(token in searchable_tokens or token in searchable_text for token in tokens)


def query_terms(value: str) -> list[str]:
    terms = canonical_alias(value).split()
    return [singularize(term) for term in terms if term]


def singularize(term: str) -> str:
    if len(term) > 3 and term.endswith("es"):
        return term[:-2]
    if len(term) > 3 and term.endswith("s"):
        return term[:-1]
    return term


def to_parsed_receipt_response(parsed, db: Session | None = None) -> ParsedReceiptRead:
    return ParsedReceiptRead(
        store_name=parsed.store_name,
        store_location_text=parsed.store_location_text,
        store_phone=parsed.store_phone,
        purchased_at=parsed.purchased_at,
        items=[
            {
                "line": item.line,
                "name": item.name,
                "quantity": item.quantity,
                "price": item.price,
                "normalization_suggestion": to_normalization_suggestion(
                    find_product_match(db, item.name) if db else None
                ),
            }
            for item in parsed.items
        ],
    )


def to_normalization_suggestion(match: ProductMatch | None) -> NormalizationSuggestionRead | None:
    if not match:
        return None
    return NormalizationSuggestionRead(
        product_id=match.product.id,
        product_name=match.product.name,
        score=round(match.score, 2),
        matched_on=match.matched_on,
        auto_match=match.auto_match,
    )
