"""Outbound export — fetch data, validate, write file, upload.

This is the 'send catalogue to Brack/Alltron' pipeline.
Simple procedural orchestration, no state machines.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Callable, List, Sequence, Union

from pydantic import BaseModel

from b2b_data_bridge.config import Settings
from b2b_data_bridge.files import make_filename, write_file, archive_file
from b2b_data_bridge.models import (
    Product, Price, Stock,
    ExternalProductRow, ExternalPricingRow, ExternalStockRow,
    product_to_row, price_to_row, stock_to_row,
)
from b2b_data_bridge.validation import validate_product_row, validate_pricing_row, validate_stock_row

logger = logging.getLogger(__name__)


# Type alias for the sFTP-like client (SftpClient or LocalClient)
Transport = object  # duck-typed: .upload(path, remote_dir) → str


# ---------------------------------------------------------------------------
# Generic export step
# ---------------------------------------------------------------------------

def _run_export(
    job_type: str,
    items: Sequence,
    mapper: Callable,
    validator: Callable,
    settings: Settings,
    transport: Transport,
    ts: datetime | None = None,
) -> dict:
    """
    Shared pipeline: map → validate → write → upload → archive.
    Returns a summary dict.
    """
    ts = ts or datetime.utcnow()

    # 1. Map internal models → external flat rows
    rows = [mapper(item) for item in items]

    # 2. Validate each row
    errors = []
    clean: List[BaseModel] = []
    for idx, row in enumerate(rows):
        row_errors = validator(row, idx)
        if row_errors:
            errors.extend(row_errors)
        else:
            clean.append(row)

    if errors:
        logger.warning("%s export: %d validation errors — skipped those rows", job_type, len(errors))
        for e in errors:
            logger.debug("  row %d field=%s: %s", e.row, e.field, e.message)

    if not clean:
        logger.error("%s export: no valid rows to export", job_type)
        return {"job_type": job_type, "exported": 0, "errors": len(errors), "file": None}

    # 3. Write file
    ext = settings.files.default_format
    filename = make_filename(job_type, ext, settings.naming, ts)
    out_path = Path(settings.paths.outbound_dir) / filename
    write_file(clean, out_path, settings.files)

    # 4. Upload
    try:
        remote = transport.upload(out_path, settings.sftp.remote_outbound_dir)  # type: ignore[attr-defined]
        logger.info("%s export: uploaded %s", job_type, remote)
    except Exception as exc:
        logger.error("%s export: upload failed — %s (local file kept at %s)", job_type, exc, out_path)
        return {"job_type": job_type, "exported": len(clean), "errors": len(errors), "file": filename, "upload_error": str(exc)}

    # 5. Archive the local copy
    try:
        archive_file(out_path, settings.paths.archive_dir)
    except OSError as exc:
        logger.warning("%s export: archive failed — %s", job_type, exc)

    return {
        "job_type": job_type,
        "exported": len(clean),
        "errors": len(errors),
        "file": filename,
    }


# ---------------------------------------------------------------------------
# Public entry points (one per data type)
# ---------------------------------------------------------------------------

def export_products(products: Sequence[Product], settings: Settings, transport: Transport, ts: datetime | None = None) -> dict:
    return _run_export("products", products, product_to_row, validate_product_row, settings, transport, ts)


def export_pricing(prices: Sequence[Price], settings: Settings, transport: Transport, ts: datetime | None = None) -> dict:
    return _run_export("pricing", prices, price_to_row, validate_pricing_row, settings, transport, ts)


def export_stock(stock: Sequence[Stock], settings: Settings, transport: Transport, ts: datetime | None = None) -> dict:
    return _run_export("stock", stock, stock_to_row, validate_stock_row, settings, transport, ts)


def run_full_export(
    products: Sequence[Product],
    prices: Sequence[Price],
    stock: Sequence[Stock],
    settings: Settings,
    transport: Transport,
) -> list[dict]:
    """Run all three outbound exports and return list of summaries."""
    ts = datetime.utcnow()
    results = [
        export_products(products, settings, transport, ts),
        export_pricing(prices, settings, transport, ts),
        export_stock(stock, settings, transport, ts),
    ]
    total = sum(r["exported"] for r in results)
    errs = sum(r["errors"] for r in results)
    logger.info("Full export complete: %d rows exported, %d errors", total, errs)
    return results
