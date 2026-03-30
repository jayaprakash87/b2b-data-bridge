"""Tests for filename generation."""

from __future__ import annotations

from datetime import datetime

import pytest

from b2b_data_bridge.config import NamingConfig
from b2b_data_bridge.files import make_filename


class TestFilenameGeneration:
    @pytest.fixture
    def naming(self) -> NamingConfig:
        return NamingConfig()

    def test_product_csv_filename(self, naming: NamingConfig) -> None:
        ts = datetime(2026, 3, 30, 14, 30, 0)
        result = make_filename("products", "csv", naming, ts)
        assert result == "PRODUCTS_20260330_143000.csv"

    def test_pricing_xlsx_filename(self, naming: NamingConfig) -> None:
        ts = datetime(2026, 1, 15, 8, 0, 0)
        result = make_filename("pricing", "xlsx", naming, ts)
        assert result == "PRICING_20260115_080000.xlsx"

    def test_stock_filename(self, naming: NamingConfig) -> None:
        ts = datetime(2026, 12, 31, 23, 59, 59)
        result = make_filename("stock", "csv", naming, ts)
        assert result == "STOCK_20261231_235959.csv"

    def test_order_filename(self, naming: NamingConfig) -> None:
        ts = datetime(2026, 6, 1, 0, 0, 0)
        result = make_filename("orders", "csv", naming, ts)
        assert result == "ORDERS_20260601_000000.csv"

    def test_custom_prefix(self) -> None:
        custom = NamingConfig(product_prefix="CATALOG")
        ts = datetime(2026, 3, 30, 10, 0, 0)
        result = make_filename("products", "csv", custom, ts)
        assert result.startswith("CATALOG_")
