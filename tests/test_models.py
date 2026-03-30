"""Tests for domain model validation rules."""

from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from b2b_data_bridge.models import (
    ExternalOrderRow,
    ExternalPricingRow,
    ExternalProductRow,
    ExternalStockRow,
    Order,
    OrderLine,
    Price,
    Product,
    Stock,
)


class TestProductModel:
    def test_valid_product(self) -> None:
        p = Product(sku="SKU-001", name="Mouse", ean="4006381333931")
        assert p.sku == "SKU-001"
        assert p.ean == "4006381333931"

    def test_invalid_ean_non_digit(self) -> None:
        with pytest.raises(ValidationError, match="EAN must contain only digits"):
            Product(sku="SKU-001", name="Mouse", ean="400638ABC3931")

    def test_invalid_ean_wrong_length(self) -> None:
        with pytest.raises(ValidationError):
            Product(sku="SKU-001", name="Mouse", ean="12345")

    def test_empty_sku_fails(self) -> None:
        with pytest.raises(ValidationError):
            Product(sku="", name="Mouse", ean="4006381333931")

    def test_empty_name_fails(self) -> None:
        with pytest.raises(ValidationError):
            Product(sku="SKU-001", name="", ean="4006381333931")


class TestPriceModel:
    def test_valid_price(self) -> None:
        p = Price(sku="SKU-001", net_price=Decimal("29.90"), currency="CHF")
        assert p.net_price == Decimal("29.90")

    def test_zero_price_fails(self) -> None:
        with pytest.raises(ValidationError):
            Price(sku="SKU-001", net_price=Decimal("0"), currency="CHF")

    def test_negative_price_fails(self) -> None:
        with pytest.raises(ValidationError):
            Price(sku="SKU-001", net_price=Decimal("-10"), currency="CHF")

    def test_invalid_currency(self) -> None:
        with pytest.raises(ValidationError):
            Price(sku="SKU-001", net_price=Decimal("10"), currency="ch")


class TestStockModel:
    def test_valid_stock(self) -> None:
        s = Stock(sku="SKU-001", quantity=100)
        assert s.quantity == 100

    def test_negative_quantity_fails(self) -> None:
        with pytest.raises(ValidationError):
            Stock(sku="SKU-001", quantity=-1)


class TestOrderModel:
    def test_valid_order(self) -> None:
        o = Order(
            order_id="ORD-001",
            order_date="2026-03-30T10:00:00",
            lines=[OrderLine(sku="SKU-001", quantity=2, net_price=Decimal("10"), currency="CHF")],
        )
        assert len(o.lines) == 1

    def test_order_without_lines_fails(self) -> None:
        with pytest.raises(ValidationError):
            Order(order_id="ORD-001", order_date="2026-03-30T10:00:00", lines=[])
