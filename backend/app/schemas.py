from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class StoreRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    location_text: str | None
    phone: str | None
    created_at: datetime


class ProductAliasRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    normalized_product_id: int
    alias: str
    created_at: datetime


class NormalizedProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    category: str | None
    created_at: datetime
    aliases: list[ProductAliasRead] = []


class ReceiptItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    receipt_id: int
    store_id: int
    normalized_product_id: int | None
    raw_item_name: str
    name: str
    normalized_product_name: str | None
    quantity: float | None
    unit: str | None
    price: float
    purchased_at: date | None


class ReceiptRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    store_id: int
    store_name: str
    purchased_at: date | None
    original_filename: str | None
    image_path: str | None
    raw_text: str
    created_at: datetime
    items: list[ReceiptItemRead] = []


class ParsedReceiptItemRead(BaseModel):
    line: str
    name: str
    quantity: str | None
    price: float


class ParsedReceiptRead(BaseModel):
    store_name: str
    store_location_text: str | None
    store_phone: str | None
    purchased_at: date | None
    items: list[ParsedReceiptItemRead]


class ReceiptPreviewResponse(BaseModel):
    image_path: str
    original_filename: str | None
    extracted_text: str
    parsed: ParsedReceiptRead


class CorrectedReceiptItem(BaseModel):
    name: str
    price: float
    quantity: str | None = None
    unit: str | None = None
    source_line: str | None = None


class SaveReceiptRequest(BaseModel):
    store_name: str
    store_location_text: str | None = None
    store_phone: str | None = None
    purchased_at: date | None = None
    image_path: str | None = None
    original_filename: str | None = None
    raw_text: str = ""
    items: list[CorrectedReceiptItem]


class SearchResult(BaseModel):
    item_id: int
    raw_item_name: str
    name: str
    normalized_product_name: str | None
    quantity: float | None
    unit: str | None
    price: float
    store_id: int
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
