"""Inbound order processing — download, parse, validate, deduplicate.

This is the 'receive orders from Brack/Alltron' pipeline.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List

from b2b_data_bridge.config import Settings
from b2b_data_bridge.files import FileParseError, parse_file, archive_file, quarantine_file
from b2b_data_bridge.models import ExternalOrderRow, Order, order_rows_to_orders
from b2b_data_bridge.validation import validate_order_row, validate_filename

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Order store interface (duck-typed, no ABC needed)
# ---------------------------------------------------------------------------

class InMemoryOrderStore:
    """Simple in-memory store. Replace with DB calls in production."""

    def __init__(self) -> None:
        self._orders: dict[str, Order] = {}

    def exists(self, order_id: str) -> bool:
        return order_id in self._orders

    def save(self, order: Order) -> None:
        self._orders[order.order_id] = order
        logger.info("Saved order %s (%d lines)", order.order_id, len(order.lines))

    def all(self) -> list[Order]:
        return list(self._orders.values())


# ---------------------------------------------------------------------------
# Inbound pipeline
# ---------------------------------------------------------------------------

def process_order_file(
    file_path: Path,
    settings: Settings,
    store: InMemoryOrderStore,
) -> dict:
    """
    Parse one order file → validate → deduplicate → save.
    Returns a summary dict.
    """
    filename = file_path.name

    # 1. Validate filename pattern
    ext = file_path.suffix.lstrip(".")
    fn_error = validate_filename(filename, settings.naming.order_prefix, ext)
    if fn_error:
        logger.warning("Bad filename %s: %s", filename, fn_error.message)
        quarantine_file(file_path, settings.paths.failed_dir, fn_error.message)
        return {"file": filename, "orders_saved": 0, "errors": 1, "status": "quarantined"}

    # 2. Parse file
    try:
        rows, parse_errors = parse_file(file_path, ExternalOrderRow, settings.files)
    except FileParseError as exc:
        logger.error("%s: %s", filename, exc)
        quarantine_file(file_path, settings.paths.failed_dir, str(exc))
        return {"file": filename, "orders_saved": 0, "errors": 1, "status": "quarantined"}

    if parse_errors:
        logger.warning("%s: %d parse errors", filename, len(parse_errors))

    if not rows and parse_errors:
        quarantine_file(file_path, settings.paths.failed_dir, "no valid rows")
        return {"file": filename, "orders_saved": 0, "errors": len(parse_errors), "status": "quarantined"}

    # 3. Validate each row
    validation_errors = []
    clean_rows: List[ExternalOrderRow] = []
    for idx, row in enumerate(rows):
        row_errs = validate_order_row(row, idx)
        if row_errs:
            validation_errors.extend(row_errs)
        else:
            clean_rows.append(row)

    # 4. Map to internal Order models (groups rows by OrderID into orders with lines)
    orders = order_rows_to_orders(clean_rows)

    # 5. Deduplicate against store (idempotency)
    saved = 0
    skipped = 0
    for order in orders:
        if store.exists(order.order_id):
            logger.debug("Order %s already exists — skipping", order.order_id)
            skipped += 1
            continue
        store.save(order)
        saved += 1

    # 6. Archive the processed file
    archive_file(file_path, settings.paths.archive_dir)

    total_errors = len(parse_errors) + len(validation_errors)
    logger.info(
        "%s: %d orders saved, %d skipped (dup), %d errors",
        filename, saved, skipped, total_errors,
    )
    return {
        "file": filename,
        "orders_saved": saved,
        "orders_skipped": skipped,
        "errors": total_errors,
        "status": "processed",
    }


_MAX_INBOUND_FILES = 100  # process at most N files per poll cycle


def poll_and_process(
    settings: Settings,
    transport,
    store: InMemoryOrderStore,
) -> list[dict]:
    """Download all pending order files from sFTP, process each one."""
    # 1. List remote files
    remote_files = transport.list_files(settings.sftp.remote_inbound_dir)
    if not remote_files:
        logger.info("No inbound files found")
        return []

    if len(remote_files) > _MAX_INBOUND_FILES:
        logger.warning(
            "Found %d inbound files, processing first %d only",
            len(remote_files), _MAX_INBOUND_FILES,
        )
        remote_files = remote_files[:_MAX_INBOUND_FILES]

    results = []
    local_inbox = Path(settings.paths.inbound_dir)

    for remote_path in remote_files:
        try:
            # 2. Download
            local_path = transport.download(remote_path, local_inbox)

            # 3. Process
            result = process_order_file(local_path, settings, store)
        except Exception as exc:
            logger.error("Failed to process %s: %s", remote_path, exc)
            results.append({"file": remote_path, "orders_saved": 0, "errors": 1, "status": "error"})
            continue

        results.append(result)

        # 4. Remove from remote server after successful processing
        if result["status"] == "processed":
            try:
                transport.remove(remote_path)
            except Exception:
                logger.warning("Could not remove remote file %s", remote_path)

    total_saved = sum(r["orders_saved"] for r in results)
    logger.info("Inbound complete: %d files, %d orders saved", len(results), total_saved)
    return results
