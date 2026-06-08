from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class ReceiptItemBase(BaseModel):
    name: str
    quantity: str | None = None
    price: float


class ReceiptItemCreate(ReceiptItemBase):
    pass


class ReceiptItemRead(ReceiptItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    receipt_id: int


class ReceiptRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    store_name: str
    purchased_at: date | None
    original_filename: str | None
    raw_text: str
    created_at: datetime
    items: list[ReceiptItemRead] = []


class SearchResult(BaseModel):
    item_id: int
    name: str
    quantity: str | None
    price: float
    store_name: str
    purchased_at: date | None
    receipt_id: int


class StorePriceSummary(BaseModel):
    store_name: str
    lowest_price: float
    highest_price: float
    average_price: float
    observations: int


class CompareResult(BaseModel):
    query: str
    matches: list[SearchResult]
    by_store: list[StorePriceSummary]
