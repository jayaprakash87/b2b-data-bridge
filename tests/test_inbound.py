"""Tests for inbound order parsing and processing."""

from __future__ import annotations

import csv
from pathlib import Path
from unittest.mock import patch

import pytest

from b2b_data_bridge.config import FileConfig, Settings
from b2b_data_bridge.orders import InMemoryOrderStore, poll_and_process, process_order_file
from b2b_data_bridge.models import ExternalOrderRow, order_rows_to_orders
from b2b_data_bridge.files import parse_csv, FileParseError


@pytest.fixture
def file_config() -> FileConfig:
    return FileConfig(encoding="utf-8", csv_delimiter=";", csv_quotechar='"')


def _write_order_csv(path: Path, rows: list[dict[str, str]], delimiter: str = ";") -> Path:
    fieldnames = [
        "OrderID", "OrderDate", "ArticleNumber", "EAN",
        "Quantity", "NetPrice", "Currency", "CustomerReference", "DeliveryAddress",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=delimiter)
        writer.writeheader()
        writer.writerows(rows)
    return path


class TestParseInboundOrders:
    def test_parse_valid_csv(self, tmp_path: Path, file_config: FileConfig) -> None:
        csv_path = _write_order_csv(tmp_path / "orders.csv", [
            {
                "OrderID": "ORD-001", "OrderDate": "2026-03-30",
                "ArticleNumber": "SKU-001", "EAN": "4006381333931",
                "Quantity": "2", "NetPrice": "29.90", "Currency": "CHF",
                "CustomerReference": "REF-100", "DeliveryAddress": "Zurich",
            },
        ])
        rows, errors = parse_csv(csv_path, ExternalOrderRow, file_config)
        assert len(rows) == 1
        assert len(errors) == 0
        assert rows[0].OrderID == "ORD-001"

    def test_parse_multiple_lines_same_order(self, tmp_path: Path, file_config: FileConfig) -> None:
        csv_path = _write_order_csv(tmp_path / "orders.csv", [
            {
                "OrderID": "ORD-001", "OrderDate": "2026-03-30",
                "ArticleNumber": "SKU-001", "EAN": "", "Quantity": "2",
                "NetPrice": "10", "Currency": "CHF",
                "CustomerReference": "", "DeliveryAddress": "",
            },
            {
                "OrderID": "ORD-001", "OrderDate": "2026-03-30",
                "ArticleNumber": "SKU-002", "EAN": "", "Quantity": "1",
                "NetPrice": "20", "Currency": "CHF",
                "CustomerReference": "", "DeliveryAddress": "",
            },
        ])
        rows, errors = parse_csv(csv_path, ExternalOrderRow, file_config)
        assert len(rows) == 2

        # Test grouping into orders
        orders = order_rows_to_orders(rows)
        assert len(orders) == 1
        assert len(orders[0].lines) == 2

    def test_parse_invalid_encoding(self, tmp_path: Path, file_config: FileConfig) -> None:
        path = tmp_path / "bad_encoding.csv"
        with open(path, "wb") as f:
            f.write(b"OrderID;OrderDate\n")
            f.write(b"ORD-001;2026-03-30\xff\n")

        with pytest.raises(FileParseError, match="Encoding error"):
            parse_csv(path, ExternalOrderRow, file_config)


class TestOrderMapping:
    def test_group_by_order_id(self) -> None:
        rows = [
            ExternalOrderRow(
                OrderID="ORD-001", OrderDate="2026-03-30",
                ArticleNumber="SKU-001", Quantity="2", NetPrice="10", Currency="CHF",
            ),
            ExternalOrderRow(
                OrderID="ORD-001", OrderDate="2026-03-30",
                ArticleNumber="SKU-002", Quantity="1", NetPrice="20", Currency="CHF",
            ),
            ExternalOrderRow(
                OrderID="ORD-002", OrderDate="2026-03-30",
                ArticleNumber="SKU-003", Quantity="3", NetPrice="15", Currency="CHF",
            ),
        ]
        orders = order_rows_to_orders(rows)
        assert len(orders) == 2
        order_map = {o.order_id: o for o in orders}
        assert len(order_map["ORD-001"].lines) == 2
        assert len(order_map["ORD-002"].lines) == 1


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_ORDER_ROW = (
    "OrderID;OrderDate;ArticleNumber;EAN;Quantity;NetPrice;Currency;"
    "CustomerReference;DeliveryAddress\n"
    "ORD-001;2026-03-30;SKU-001;4006381333931;2;29.90;CHF;REF;Zurich\n"
)


def _write_valid_order_file(path: Path) -> Path:
    path.write_text(_VALID_ORDER_ROW, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# InMemoryOrderStore
# ---------------------------------------------------------------------------

class TestInMemoryOrderStore:
    def test_all_returns_empty_list_initially(self) -> None:
        store = InMemoryOrderStore()
        assert store.all() == []

    def test_save_then_all(self) -> None:
        from b2b_data_bridge.models import Order, OrderLine
        from decimal import Decimal
        from datetime import datetime

        store = InMemoryOrderStore()
        line = OrderLine(sku="SKU-001", quantity=1, net_price=Decimal("10"), currency="CHF")
        order = Order(
            order_id="ORD-001",
            order_date=datetime(2026, 3, 30),
            lines=[line],
        )
        store.save(order)
        assert len(store.all()) == 1
        assert store.exists("ORD-001")


# ---------------------------------------------------------------------------
# process_order_file
# ---------------------------------------------------------------------------

class TestProcessOrderFile:
    def test_bad_filename_quarantined(self, tmp_path: Path, settings: Settings) -> None:
        bad_file = tmp_path / "bad_name.csv"
        bad_file.write_text(_VALID_ORDER_ROW, encoding="utf-8")

        result = process_order_file(bad_file, settings, InMemoryOrderStore())

        assert result["status"] == "quarantined"
        assert not bad_file.exists()

    def test_file_parse_error_quarantined(self, tmp_path: Path, settings: Settings) -> None:
        order_file = tmp_path / "ORDERS_20260330_120000.csv"
        order_file.write_bytes(b"OrderID;OrderDate\nORD\xff;bad\n")  # non-UTF-8

        result = process_order_file(order_file, settings, InMemoryOrderStore())

        assert result["status"] == "quarantined"

    def test_no_valid_rows_quarantined(self, tmp_path: Path, settings: Settings) -> None:
        # Wrong column headers → all rows fail required-field validation
        order_file = tmp_path / "ORDERS_20260330_120000.csv"
        order_file.write_text("WrongCol1;WrongCol2\nval1;val2\n", encoding="utf-8")

        result = process_order_file(order_file, settings, InMemoryOrderStore())

        assert result["status"] == "quarantined"

    def test_valid_file_saved(self, tmp_path: Path, settings: Settings) -> None:
        order_file = tmp_path / "ORDERS_20260330_120000.csv"
        _write_valid_order_file(order_file)

        store = InMemoryOrderStore()
        result = process_order_file(order_file, settings, store)

        assert result["status"] == "processed"
        assert result["orders_saved"] == 1
        assert len(store.all()) == 1

    def test_duplicate_order_skipped(self, tmp_path: Path, settings: Settings) -> None:
        order_file = tmp_path / "ORDERS_20260330_120000.csv"
        _write_valid_order_file(order_file)

        store = InMemoryOrderStore()
        process_order_file(order_file, settings, store)

        # Process again with a new file containing the same OrderID
        order_file2 = tmp_path / "ORDERS_20260330_130000.csv"
        _write_valid_order_file(order_file2)
        result = process_order_file(order_file2, settings, store)

        assert result["orders_skipped"] == 1
        assert result["orders_saved"] == 0


# ---------------------------------------------------------------------------
# poll_and_process
# ---------------------------------------------------------------------------

class TestPollAndProcess:
    def test_no_remote_files_returns_empty(self, settings: Settings) -> None:
        class EmptyTransport:
            def list_files(self, remote_dir: str) -> list:
                return []

        result = poll_and_process(settings, EmptyTransport(), InMemoryOrderStore())
        assert result == []

    def test_download_exception_recorded_as_error(self, settings: Settings) -> None:
        class FailDownloadTransport:
            def list_files(self, remote_dir: str) -> list:
                return ["/inbound/ORDERS_20260330_120000.csv"]

            def download(self, remote_path: str, local_dir: Path) -> Path:
                raise OSError("network error")

        results = poll_and_process(settings, FailDownloadTransport(), InMemoryOrderStore())

        assert len(results) == 1
        assert results[0]["status"] == "error"

    def test_successful_file_removed_from_remote(
        self, tmp_path: Path, settings: Settings,
    ) -> None:
        removed: list[str] = []

        class MockTransport:
            def list_files(self, remote_dir: str) -> list:
                return ["/inbound/ORDERS_20260330_120000.csv"]

            def download(self, remote_path: str, local_dir: Path) -> Path:
                local_dir.mkdir(parents=True, exist_ok=True)
                dest = local_dir / "ORDERS_20260330_120000.csv"
                dest.write_text(_VALID_ORDER_ROW, encoding="utf-8")
                return dest

            def remove(self, remote_path: str) -> None:
                removed.append(remote_path)

        poll_and_process(settings, MockTransport(), InMemoryOrderStore())

        assert "/inbound/ORDERS_20260330_120000.csv" in removed

    def test_file_limit_caps_processing(self, settings: Settings) -> None:
        class BigTransport:
            def list_files(self, remote_dir: str) -> list:
                return [f"/inbound/ORDERS_2026033{i}_120000.csv" for i in range(5)]

            def download(self, remote_path: str, local_dir: Path) -> Path:
                raise OSError("stop early")

        with patch("b2b_data_bridge.orders._MAX_INBOUND_FILES", 2):
            results = poll_and_process(settings, BigTransport(), InMemoryOrderStore())

        assert len(results) == 2
