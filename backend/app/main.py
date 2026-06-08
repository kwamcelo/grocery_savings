from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from .db import Base, engine, get_db
from .models import Receipt, ReceiptItem
from .schemas import CompareResult, ReceiptRead, SearchResult, StorePriceSummary
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

    receipt = Receipt(
        store_name=parsed.store_name,
        purchased_at=parsed.purchased_at,
        original_filename=file.filename,
        raw_text=raw_text,
    )
    receipt.items = [
        ReceiptItem(name=item.name, quantity=item.quantity, price=item.price)
        for item in parsed.items
    ]

    db.add(receipt)
    db.commit()
    db.refresh(receipt)
    return receipt


@app.get("/receipts", response_model=list[ReceiptRead])
def list_receipts(db: Session = Depends(get_db)) -> list[Receipt]:
    return list(
        db.scalars(
            select(Receipt)
            .options(selectinload(Receipt.items))
            .order_by(Receipt.created_at.desc())
        )
    )


@app.get("/items/search", response_model=list[SearchResult])
def search_items(q: str, db: Session = Depends(get_db)) -> list[SearchResult]:
    rows = db.execute(
        select(ReceiptItem, Receipt)
        .join(Receipt)
        .where(ReceiptItem.name.ilike(f"%{q}%"))
        .order_by(ReceiptItem.name.asc(), Receipt.purchased_at.desc().nullslast())
    ).all()
    return [to_search_result(item, receipt) for item, receipt in rows]


@app.get("/items/compare", response_model=CompareResult)
def compare_items(name: str, db: Session = Depends(get_db)) -> CompareResult:
    rows = db.execute(
        select(ReceiptItem, Receipt)
        .join(Receipt)
        .where(ReceiptItem.name.ilike(f"%{name}%"))
        .order_by(ReceiptItem.price.asc())
    ).all()

    summaries = db.execute(
        select(
            Receipt.store_name,
            func.min(ReceiptItem.price),
            func.max(ReceiptItem.price),
            func.avg(ReceiptItem.price),
            func.count(ReceiptItem.id),
        )
        .join(ReceiptItem)
        .where(ReceiptItem.name.ilike(f"%{name}%"))
        .group_by(Receipt.store_name)
        .order_by(func.avg(ReceiptItem.price).asc())
    ).all()

    return CompareResult(
        query=name,
        matches=[to_search_result(item, receipt) for item, receipt in rows],
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


def to_search_result(item: ReceiptItem, receipt: Receipt) -> SearchResult:
    return SearchResult(
        item_id=item.id,
        name=item.name,
        quantity=item.quantity,
        price=item.price,
        store_name=receipt.store_name,
        purchased_at=receipt.purchased_at,
        receipt_id=receipt.id,
    )
