"""Data models — what the data looks like, validated with pydantic.

Three layers:
  1. Internal models (Product, Price, Stock, Order) — our representation
  2. External row models (ExternalProductRow, etc.) — the distributor's CSV schema
  3. Mapping functions between the two
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Optional

from pydantic import BaseModel, Field, ValidationError, field_validator


# ---------------------------------------------------------------------------
# Internal domain models
# ---------------------------------------------------------------------------


class Product(BaseModel):
    sku: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    ean: str = Field(..., min_length=8, max_length=14)
    description: str = ""
    category: str = ""
    brand: str = ""
    weight_kg: Optional[Decimal] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("ean")
    @classmethod
    def ean_must_be_digits(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("EAN must contain only digits")
        if len(v) not in (8, 12, 13, 14):
            raise ValueError("EAN must be 8, 12, 13, or 14 digits")
        return v


class Price(BaseModel):
    sku: str = Field(..., min_length=1)
    net_price: Decimal = Field(..., gt=0)
    gross_price: Optional[Decimal] = None
    currency: str = Field(..., pattern=r"^[A-Z]{3}$")
    price_unit: int = Field(default=1, ge=1)
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None


class Stock(BaseModel):
    sku: str = Field(..., min_length=1)
    quantity: int = Field(..., ge=0)
    warehouse: str = ""
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class OrderLine(BaseModel):
    sku: str = Field(..., min_length=1)
    ean: str = ""
    quantity: int = Field(..., ge=1)
    net_price: Decimal = Field(..., gt=0)
    currency: str = Field(..., pattern=r"^[A-Z]{3}$")


class Order(BaseModel):
    order_id: str = Field(..., min_length=1)
    order_date: datetime
    customer_ref: str = ""
    delivery_address: str = ""
    lines: list[OrderLine] = Field(default_factory=list, min_length=1)


# ---------------------------------------------------------------------------
# External row models — flat CSV/XLSX rows the distributor expects/sends
# ---------------------------------------------------------------------------


class ExternalProductRow(BaseModel):
    ArticleNumber: str
    ArticleName: str
    EAN: str
    Description: str = ""
    Category: str = ""
    Brand: str = ""
    WeightKG: str = ""
    LastUpdate: str = ""


class ExternalPricingRow(BaseModel):
    ArticleNumber: str
    NetPrice: str
    GrossPrice: str = ""
    Currency: str
    PriceUnit: str = "1"
    ValidFrom: str = ""
    ValidTo: str = ""


class ExternalStockRow(BaseModel):
    ArticleNumber: str
    AvailableQty: str
    Warehouse: str = ""
    RestockDate: str = ""
    LastUpdate: str = ""


class ExternalOrderRow(BaseModel):
    OrderID: str
    OrderDate: str
    ArticleNumber: str
    EAN: str = ""
    Quantity: str
    NetPrice: str
    Currency: str
    CustomerReference: str = ""
    DeliveryAddress: str = ""


# ---------------------------------------------------------------------------
# Mapping: Internal → External (for outbound exports)
# ---------------------------------------------------------------------------

_TS = "%Y-%m-%dT%H:%M:%S"


def product_to_row(p: Product) -> ExternalProductRow:
    return ExternalProductRow(
        ArticleNumber=p.sku, ArticleName=p.name, EAN=p.ean,
        Description=p.description, Category=p.category, Brand=p.brand,
        WeightKG=str(p.weight_kg) if p.weight_kg is not None else "",
        LastUpdate=p.updated_at.strftime(_TS),
    )


def price_to_row(p: Price) -> ExternalPricingRow:
    return ExternalPricingRow(
        ArticleNumber=p.sku, NetPrice=str(p.net_price),
        GrossPrice=str(p.gross_price) if p.gross_price is not None else "",
        Currency=p.currency, PriceUnit=str(p.price_unit),
        ValidFrom=p.valid_from.strftime(_TS) if p.valid_from else "",
        ValidTo=p.valid_to.strftime(_TS) if p.valid_to else "",
    )


def stock_to_row(s: Stock) -> ExternalStockRow:
    return ExternalStockRow(
        ArticleNumber=s.sku, AvailableQty=str(s.quantity),
        Warehouse=s.warehouse,
        LastUpdate=s.updated_at.strftime(_TS),
    )


# ---------------------------------------------------------------------------
# Mapping: External → Internal (for inbound orders)
# ---------------------------------------------------------------------------


def order_rows_to_orders(rows: list[ExternalOrderRow]) -> list[Order]:
    """Group flat order rows by OrderID into Order objects with lines."""
    grouped: dict[str, list[ExternalOrderRow]] = {}
    for row in rows:
        grouped.setdefault(row.OrderID, []).append(row)

    orders: list[Order] = []
    for order_id, group in grouped.items():
        try:
            first = group[0]
            lines = [
                OrderLine(
                    sku=r.ArticleNumber, ean=r.EAN, quantity=int(r.Quantity),
                    net_price=Decimal(r.NetPrice), currency=r.Currency,
                )
                for r in group
            ]
            orders.append(Order(
                order_id=order_id,
                order_date=_parse_datetime(first.OrderDate),
                customer_ref=first.CustomerReference,
                delivery_address=first.DeliveryAddress,
                lines=lines,
            ))
        except (ValueError, InvalidOperation, ValidationError) as exc:
            import logging
            logging.getLogger(__name__).warning(
                "Skipping order %s: %s", order_id, exc,
            )
    return orders


def _parse_datetime(value: str) -> datetime:
    for fmt in (_TS, "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise ValueError(f"Cannot parse datetime: {value}")
