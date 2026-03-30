"""Tests for model mapping functions."""

from __future__ import annotations

from decimal import Decimal

import pytest

from b2b_data_bridge.models import Price, Product, Stock, product_to_row, price_to_row, stock_to_row


class TestProductMapper:
    def test_product_to_external(self) -> None:
        p = Product(
            sku="SKU-001", name="Mouse", ean="4006381333931",
            description="Wireless", category="Peripherals", brand="TechCorp",
            weight_kg=Decimal("0.12"),
        )
        ext = product_to_row(p)
        assert ext.ArticleNumber == "SKU-001"
        assert ext.ArticleName == "Mouse"
        assert ext.EAN == "4006381333931"
        assert ext.WeightKG == "0.12"

    def test_batch_mapping(self) -> None:
        products = [
            Product(sku="SKU-001", name="A", ean="4006381333931"),
            Product(sku="SKU-002", name="B", ean="4006381333948"),
        ]
        result = [product_to_row(p) for p in products]
        assert len(result) == 2


class TestPriceMapper:
    def test_price_to_external(self) -> None:
        p = Price(sku="SKU-001", net_price=Decimal("29.90"), gross_price=Decimal("32.29"), currency="CHF")
        ext = price_to_row(p)
        assert ext.ArticleNumber == "SKU-001"
        assert ext.NetPrice == "29.90"
        assert ext.GrossPrice == "32.29"
        assert ext.Currency == "CHF"

    def test_optional_fields(self) -> None:
        p = Price(sku="SKU-001", net_price=Decimal("10"), currency="EUR")
        ext = price_to_row(p)
        assert ext.GrossPrice == ""


class TestStockMapper:
    def test_stock_to_external(self) -> None:
        s = Stock(sku="SKU-001", quantity=150, warehouse="WH-ZH")
        ext = stock_to_row(s)
        assert ext.ArticleNumber == "SKU-001"
        assert ext.AvailableQty == "150"
        assert ext.Warehouse == "WH-ZH"
