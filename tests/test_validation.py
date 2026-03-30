"""Tests for the validation engine."""

from __future__ import annotations


from b2b_data_bridge.models import (
    ExternalOrderRow,
    ExternalPricingRow,
    ExternalProductRow,
    ExternalStockRow,
)
from b2b_data_bridge.validation import (
    find_duplicate_order_ids,
    is_valid_ean,
    validate_batch,
    validate_filename,
    validate_order_row,
    validate_pricing_row,
    validate_product_row,
    validate_stock_row,
)


# ---------------------------------------------------------------------------
# EAN validation
# ---------------------------------------------------------------------------


class TestEanValidation:
    def test_valid_ean13(self) -> None:
        assert is_valid_ean("4006381333931") is True

    def test_valid_ean8(self) -> None:
        assert is_valid_ean("96385074") is True

    def test_invalid_checksum(self) -> None:
        assert is_valid_ean("4006381333932") is False

    def test_non_digit(self) -> None:
        assert is_valid_ean("400638ABC3931") is False

    def test_wrong_length(self) -> None:
        assert is_valid_ean("12345") is False

    def test_empty(self) -> None:
        assert is_valid_ean("") is False


# ---------------------------------------------------------------------------
# Product row validation
# ---------------------------------------------------------------------------


class TestProductRowValidation:
    def _row(self, **overrides: str) -> ExternalProductRow:
        defaults = {
            "ArticleNumber": "SKU-001",
            "ArticleName": "Test Product",
            "EAN": "4006381333931",
        }
        defaults.update(overrides)
        return ExternalProductRow(**defaults)

    def test_valid_row(self) -> None:
        errors = validate_product_row(self._row(), 0)
        assert errors == []

    def test_missing_sku(self) -> None:
        errors = validate_product_row(self._row(ArticleNumber=""), 0)
        assert any(e.field == "ArticleNumber" for e in errors)

    def test_missing_ean(self) -> None:
        errors = validate_product_row(self._row(EAN=""), 0)
        assert any(e.field == "EAN" for e in errors)

    def test_invalid_ean_checksum(self) -> None:
        errors = validate_product_row(self._row(EAN="4006381333932"), 0)
        assert any("check-digit" in e.message for e in errors)

    def test_missing_name(self) -> None:
        errors = validate_product_row(self._row(ArticleName=""), 0)
        assert any(e.field == "ArticleName" for e in errors)


# ---------------------------------------------------------------------------
# Pricing row validation
# ---------------------------------------------------------------------------


class TestPricingRowValidation:
    def _row(self, **overrides: str) -> ExternalPricingRow:
        defaults = {
            "ArticleNumber": "SKU-001",
            "NetPrice": "29.90",
            "Currency": "CHF",
        }
        defaults.update(overrides)
        return ExternalPricingRow(**defaults)

    def test_valid_row(self) -> None:
        errors = validate_pricing_row(self._row(), 0)
        assert errors == []

    def test_zero_price(self) -> None:
        errors = validate_pricing_row(self._row(NetPrice="0"), 0)
        assert any(e.field == "NetPrice" for e in errors)

    def test_negative_price(self) -> None:
        errors = validate_pricing_row(self._row(NetPrice="-10"), 0)
        assert any(e.field == "NetPrice" for e in errors)

    def test_non_numeric_price(self) -> None:
        errors = validate_pricing_row(self._row(NetPrice="abc"), 0)
        assert any(e.field == "NetPrice" for e in errors)

    def test_invalid_currency(self) -> None:
        errors = validate_pricing_row(self._row(Currency="ch"), 0)
        assert any(e.field == "Currency" for e in errors)


# ---------------------------------------------------------------------------
# Stock row validation
# ---------------------------------------------------------------------------


class TestStockRowValidation:
    def _row(self, **overrides: str) -> ExternalStockRow:
        defaults = {"ArticleNumber": "SKU-001", "AvailableQty": "100"}
        defaults.update(overrides)
        return ExternalStockRow(**defaults)

    def test_valid(self) -> None:
        assert validate_stock_row(self._row(), 0) == []

    def test_negative_qty(self) -> None:
        errors = validate_stock_row(self._row(AvailableQty="-1"), 0)
        assert any(e.field == "AvailableQty" for e in errors)

    def test_non_numeric_qty(self) -> None:
        errors = validate_stock_row(self._row(AvailableQty="abc"), 0)
        assert any(e.field == "AvailableQty" for e in errors)


# ---------------------------------------------------------------------------
# Order row validation
# ---------------------------------------------------------------------------


class TestOrderRowValidation:
    def _row(self, **overrides: str) -> ExternalOrderRow:
        defaults = {
            "OrderID": "ORD-001",
            "OrderDate": "2026-03-30",
            "ArticleNumber": "SKU-001",
            "EAN": "4006381333931",
            "Quantity": "2",
            "NetPrice": "29.90",
            "Currency": "CHF",
        }
        defaults.update(overrides)
        return ExternalOrderRow(**defaults)

    def test_valid(self) -> None:
        assert validate_order_row(self._row(), 0) == []

    def test_missing_order_id(self) -> None:
        errors = validate_order_row(self._row(OrderID=""), 0)
        assert any(e.field == "OrderID" for e in errors)

    def test_zero_quantity(self) -> None:
        errors = validate_order_row(self._row(Quantity="0"), 0)
        assert any(e.field == "Quantity" for e in errors)

    def test_negative_price(self) -> None:
        errors = validate_order_row(self._row(NetPrice="-5"), 0)
        assert any(e.field == "NetPrice" for e in errors)


# ---------------------------------------------------------------------------
# Batch validation
# ---------------------------------------------------------------------------


class TestBatchValidation:
    def test_all_valid(self) -> None:
        rows = [
            ExternalProductRow(ArticleNumber="SKU-001", ArticleName="A", EAN="4006381333931"),
            ExternalProductRow(ArticleNumber="SKU-002", ArticleName="B", EAN="4006381333948"),
        ]
        valid, errors = validate_batch(rows, validate_product_row)
        assert len(errors) == 0
        assert len(valid) == 2

    def test_mixed_valid_invalid(self) -> None:
        rows = [
            ExternalProductRow(ArticleNumber="SKU-001", ArticleName="A", EAN="4006381333931"),
            ExternalProductRow(ArticleNumber="", ArticleName="B", EAN="4006381333948"),
        ]
        valid, errors = validate_batch(rows, validate_product_row)
        assert len(errors) > 0
        assert len(valid) == 1


# ---------------------------------------------------------------------------
# Duplicate detection
# ---------------------------------------------------------------------------


class TestDuplicateDetection:
    def _order_row(self, order_id: str) -> ExternalOrderRow:
        return ExternalOrderRow(
            OrderID=order_id, OrderDate="2026-03-30", ArticleNumber="SKU-001",
            Quantity="1", NetPrice="10", Currency="CHF",
        )

    def test_no_duplicates(self) -> None:
        rows = [self._order_row("ORD-1"), self._order_row("ORD-2")]
        unique, dups = find_duplicate_order_ids(rows)
        assert len(unique) == 2
        assert len(dups) == 0

    def test_with_duplicates(self) -> None:
        rows = [self._order_row("ORD-1"), self._order_row("ORD-1"), self._order_row("ORD-2")]
        unique, dups = find_duplicate_order_ids(rows)
        assert len(unique) == 2
        assert len(dups) == 1
        assert dups[0].OrderID == "ORD-1"


# ---------------------------------------------------------------------------
# Filename validation
# ---------------------------------------------------------------------------


class TestFilenameValidation:
    def test_valid_filename(self) -> None:
        err = validate_filename("PRODUCTS_20260330_143000.csv", "PRODUCTS", "csv")
        assert err is None

    def test_wrong_prefix(self) -> None:
        err = validate_filename("WRONG_20260330_143000.csv", "PRODUCTS", "csv")
        assert err is not None

    def test_wrong_extension(self) -> None:
        err = validate_filename("PRODUCTS_20260330_143000.xlsx", "PRODUCTS", "csv")
        assert err is not None

    def test_empty_filename(self) -> None:
        err = validate_filename("", "PRODUCTS", "csv")
        assert err is not None
        assert "empty" in err.message.lower()

    def test_bad_format(self) -> None:
        err = validate_filename("PRODUCTS_2026.csv", "PRODUCTS", "csv")
        assert err is not None
