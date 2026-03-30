"""Validation — field checks, EAN verification, duplicate detection.

Kept deliberately simple: each validator is a plain function that returns
a list of error dicts. No framework, no class hierarchy.
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any, Callable, Sequence

from pydantic import BaseModel

from b2b_data_bridge.models import (
    ExternalOrderRow,
    ExternalPricingRow,
    ExternalProductRow,
    ExternalStockRow,
)


# ---------------------------------------------------------------------------
# Lightweight validation result
# ---------------------------------------------------------------------------


class ValidationError:
    """Single field-level error — plain object, not pydantic overhead."""
    __slots__ = ("row", "field", "value", "message")

    def __init__(self, row: int | None, field: str, value: Any, message: str) -> None:
        self.row = row
        self.field = field
        self.value = value
        self.message = message

    def __repr__(self) -> str:
        return f"ValidationError(row={self.row}, field={self.field!r}, msg={self.message!r})"


# ---------------------------------------------------------------------------
# EAN / GTIN check-digit (GS1 standard)
# ---------------------------------------------------------------------------


def is_valid_ean(ean: str) -> bool:
    """Validate EAN/GTIN using the GS1 check-digit algorithm."""
    if not ean.isdigit() or len(ean) not in (8, 12, 13, 14):
        return False
    digits = [int(d) for d in ean]
    check = digits[-1]
    total = sum(d * (3 if i % 2 == 0 else 1) for i, d in enumerate(reversed(digits[:-1])))
    return (10 - (total % 10)) % 10 == check


# ---------------------------------------------------------------------------
# Small reusable checks
# ---------------------------------------------------------------------------


def _require(value: Any, field: str, row: int) -> ValidationError | None:
    if value is None or (isinstance(value, str) and not value.strip()):
        return ValidationError(row, field, value, f"{field} is required")
    return None


def _positive_decimal(value: Any, field: str, row: int) -> ValidationError | None:
    try:
        if Decimal(str(value)) <= 0:
            return ValidationError(row, field, value, f"{field} must be > 0")
    except (InvalidOperation, ValueError, TypeError):
        return ValidationError(row, field, value, f"{field} is not a valid number")
    return None


def _non_negative_int(value: Any, field: str, row: int) -> ValidationError | None:
    try:
        if int(value) < 0:
            return ValidationError(row, field, value, f"{field} must be >= 0")
    except (ValueError, TypeError):
        return ValidationError(row, field, value, f"{field} is not a valid integer")
    return None


def _valid_currency(value: Any, row: int) -> ValidationError | None:
    if not isinstance(value, str) or not re.match(r"^[A-Z]{3}$", value):
        return ValidationError(row, "Currency", value, "Currency must be 3-letter ISO code")
    return None


# ---------------------------------------------------------------------------
# Row-level validators — one per entity type
# ---------------------------------------------------------------------------


def validate_product_row(row: ExternalProductRow, idx: int) -> list[ValidationError]:
    errors: list[ValidationError] = []
    for f, v in [("ArticleNumber", row.ArticleNumber), ("ArticleName", row.ArticleName)]:
        e = _require(v, f, idx)
        if e:
            errors.append(e)
    e = _require(row.EAN, "EAN", idx)
    if e:
        errors.append(e)
    elif not is_valid_ean(row.EAN):
        errors.append(ValidationError(idx, "EAN", row.EAN, "EAN failed check-digit validation"))
    return errors


def validate_pricing_row(row: ExternalPricingRow, idx: int) -> list[ValidationError]:
    errors: list[ValidationError] = []
    e = _require(row.ArticleNumber, "ArticleNumber", idx)
    if e:
        errors.append(e)
    e = _positive_decimal(row.NetPrice, "NetPrice", idx)
    if e:
        errors.append(e)
    e = _valid_currency(row.Currency, idx)
    if e:
        errors.append(e)
    return errors


def validate_stock_row(row: ExternalStockRow, idx: int) -> list[ValidationError]:
    errors: list[ValidationError] = []
    e = _require(row.ArticleNumber, "ArticleNumber", idx)
    if e:
        errors.append(e)
    e = _non_negative_int(row.AvailableQty, "AvailableQty", idx)
    if e:
        errors.append(e)
    return errors


def validate_order_row(row: ExternalOrderRow, idx: int) -> list[ValidationError]:
    errors: list[ValidationError] = []
    for f, v in [("OrderID", row.OrderID), ("ArticleNumber", row.ArticleNumber)]:
        e = _require(v, f, idx)
        if e:
            errors.append(e)
    e = _positive_decimal(row.NetPrice, "NetPrice", idx)
    if e:
        errors.append(e)
    e = _non_negative_int(row.Quantity, "Quantity", idx)
    if e:
        errors.append(e)
    elif int(row.Quantity) < 1:
        errors.append(ValidationError(idx, "Quantity", row.Quantity, "Quantity must be >= 1"))
    e = _valid_currency(row.Currency, idx)
    if e:
        errors.append(e)
    return errors


# ---------------------------------------------------------------------------
# Batch validator
# ---------------------------------------------------------------------------

RowValidator = Callable[[Any, int], list[ValidationError]]


def validate_batch(
    rows: Sequence[BaseModel],
    validator: RowValidator,
) -> tuple[list[BaseModel], list[ValidationError]]:
    """Validate rows; return (valid_rows, all_errors)."""
    valid: list[BaseModel] = []
    errors: list[ValidationError] = []
    for idx, row in enumerate(rows):
        row_errors = validator(row, idx)
        if row_errors:
            errors.extend(row_errors)
        else:
            valid.append(row)
    return valid, errors


# ---------------------------------------------------------------------------
# Duplicate detection
# ---------------------------------------------------------------------------


def find_duplicate_order_ids(
    rows: Sequence[ExternalOrderRow],
) -> tuple[list[ExternalOrderRow], list[ExternalOrderRow]]:
    """Split into (unique, duplicates) by OrderID."""
    seen: set[str] = set()
    unique: list[ExternalOrderRow] = []
    dupes: list[ExternalOrderRow] = []
    for row in rows:
        (dupes if row.OrderID in seen else unique).append(row)
        seen.add(row.OrderID)
    return unique, dupes


# ---------------------------------------------------------------------------
# Filename validation
# ---------------------------------------------------------------------------


def validate_filename(filename: str, expected_prefix: str, expected_ext: str) -> ValidationError | None:
    if not filename:
        return ValidationError(None, "filename", filename, "Filename is empty")
    pattern = rf"^{re.escape(expected_prefix)}_\d{{8}}_\d{{6}}\.{re.escape(expected_ext)}$"
    if not re.match(pattern, filename):
        return ValidationError(
            None, "filename", filename,
            f"Expected pattern: {expected_prefix}_YYYYMMDD_HHMMSS.{expected_ext}",
        )
    return None