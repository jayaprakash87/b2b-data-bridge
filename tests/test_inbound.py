"""Tests for inbound order parsing and processing."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from b2b_data_bridge.config import FileConfig
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
