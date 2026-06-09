from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class Store(Base):
    __tablename__ = "stores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    location_text: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    receipts: Mapped[list["Receipt"]] = relationship("Receipt", back_populates="store")
    receipt_items: Mapped[list["ReceiptItem"]] = relationship(
        "ReceiptItem",
        back_populates="store",
    )


class NormalizedProduct(Base):
    __tablename__ = "normalized_products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    category: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    aliases: Mapped[list["ProductAlias"]] = relationship(
        "ProductAlias",
        back_populates="normalized_product",
        cascade="all, delete-orphan",
    )
    receipt_items: Mapped[list["ReceiptItem"]] = relationship(
        "ReceiptItem",
        back_populates="normalized_product",
    )


class ProductAlias(Base):
    __tablename__ = "product_aliases"
    __table_args__ = (UniqueConstraint("alias", name="uq_product_aliases_alias"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    normalized_product_id: Mapped[int] = mapped_column(
        ForeignKey("normalized_products.id"),
        index=True,
    )
    alias: Mapped[str] = mapped_column(String(255), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    normalized_product: Mapped[NormalizedProduct] = relationship(
        "NormalizedProduct",
        back_populates="aliases",
    )


class Receipt(Base):
    __tablename__ = "receipts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"), index=True)
    purchased_at: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    image_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    raw_text: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    store: Mapped[Store] = relationship("Store", back_populates="receipts")
    items: Mapped[list["ReceiptItem"]] = relationship(
        "ReceiptItem",
        back_populates="receipt",
        cascade="all, delete-orphan",
    )

    @property
    def store_name(self) -> str:
        return self.store.name


class ReceiptItem(Base):
    __tablename__ = "receipt_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    receipt_id: Mapped[int] = mapped_column(ForeignKey("receipts.id"), index=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"), index=True)
    normalized_product_id: Mapped[int | None] = mapped_column(
        ForeignKey("normalized_products.id"),
        nullable=True,
        index=True,
    )
    raw_item_name: Mapped[str] = mapped_column(String(255), index=True)
    price: Mapped[float] = mapped_column(Float)
    quantity: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(40), nullable=True)
    unit_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit_price_unit: Mapped[str | None] = mapped_column(String(40), nullable=True)
    purchased_at: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)

    receipt: Mapped[Receipt] = relationship("Receipt", back_populates="items")
    store: Mapped[Store] = relationship("Store", back_populates="receipt_items")
    normalized_product: Mapped[NormalizedProduct | None] = relationship(
        "NormalizedProduct",
        back_populates="receipt_items",
    )

    @property
    def name(self) -> str:
        if self.normalized_product:
            return self.normalized_product.name
        return self.raw_item_name

    @property
    def normalized_product_name(self) -> str | None:
        return self.normalized_product.name if self.normalized_product else None
