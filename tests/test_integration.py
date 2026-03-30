"""Integration tests for outbound and inbound pipelines."""

from __future__ import annotations

import csv
from decimal import Decimal
from pathlib import Path


from b2b_data_bridge.config import Settings
from b2b_data_bridge.export import export_products, export_pricing, export_stock, run_full_export
from b2b_data_bridge.models import Price, Product, Stock
from b2b_data_bridge.orders import InMemoryOrderStore, poll_and_process, process_order_file
from b2b_data_bridge.sftp import LocalClient


# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

_PRODUCTS = [
    Product(sku="SKU-001", name="Mouse", ean="4006381333931",
            description="Wireless mouse", category="Peripherals",
            brand="TechCorp", weight_kg=Decimal("0.12")),
    Product(sku="SKU-002", name="USB-C Hub", ean="4006381333948",
            description="7-port hub", category="Accessories",
            brand="TechCorp", weight_kg=Decimal("0.25")),
    Product(sku="SKU-003", name="Keyboard", ean="5901234123457",
            description="Mechanical keyboard", category="Peripherals",
            brand="KeyPro"),
    Product(sku="SKU-004", name="Monitor Stand", ean="4007249902122",
            category="Furniture", brand="DeskWorks"),
    Product(sku="SKU-005", name="Webcam HD", ean="8710103917083",
            category="Peripherals", brand="VisionTech"),
]

_PRICES = [
    Price(sku="SKU-001", net_price=Decimal("29.90"), gross_price=Decimal("32.29"), currency="CHF"),
    Price(sku="SKU-002", net_price=Decimal("49.90"), currency="CHF"),
    Price(sku="SKU-003", net_price=Decimal("89.00"), currency="CHF"),
    Price(sku="SKU-004", net_price=Decimal("39.90"), currency="CHF"),
    Price(sku="SKU-005", net_price=Decimal("59.90"), currency="CHF"),
]

_STOCK = [
    Stock(sku="SKU-001", quantity=150, warehouse="WH-ZH"),
    Stock(sku="SKU-002", quantity=75, warehouse="WH-ZH"),
    Stock(sku="SKU-003", quantity=200, warehouse="WH-BE"),
    Stock(sku="SKU-004", quantity=50, warehouse="WH-ZH"),
    Stock(sku="SKU-005", quantity=120, warehouse="WH-BE"),
]


# ---------------------------------------------------------------------------
# Outbound tests
# ---------------------------------------------------------------------------


class TestOutboundIntegration:
    def test_export_products(self, settings: Settings, tmp_data_dir: Path) -> None:
        transport = LocalClient(str(tmp_data_dir / "sftp_mock"))
        result = export_products(_PRODUCTS, settings, transport)
        assert result["exported"] == 5
        assert result["errors"] == 0
        assert result["file"] is not None

    def test_export_pricing(self, settings: Settings, tmp_data_dir: Path) -> None:
        transport = LocalClient(str(tmp_data_dir / "sftp_mock"))
        result = export_pricing(_PRICES, settings, transport)
        assert result["exported"] == 5
        assert result["errors"] == 0

    def test_export_stock(self, settings: Settings, tmp_data_dir: Path) -> None:
        transport = LocalClient(str(tmp_data_dir / "sftp_mock"))
        result = export_stock(_STOCK, settings, transport)
        assert result["exported"] == 5
        assert result["errors"] == 0

    def test_export_all(self, settings: Settings, tmp_data_dir: Path) -> None:
        transport = LocalClient(str(tmp_data_dir / "sftp_mock"))
        results = run_full_export(_PRODUCTS, _PRICES, _STOCK, settings, transport)
        assert len(results) == 3
        assert all(r["exported"] == 5 for r in results)


# ---------------------------------------------------------------------------
# Inbound tests
# ---------------------------------------------------------------------------


def _place_order_file(inbound_dir: Path, rows: list[dict[str, str]],
                      filename: str = "ORDERS_20260330_100000.csv") -> Path:
    inbound_dir.mkdir(parents=True, exist_ok=True)
    path = inbound_dir / filename
    fieldnames = [
        "OrderID", "OrderDate", "ArticleNumber", "EAN",
        "Quantity", "NetPrice", "Currency", "CustomerReference", "DeliveryAddress",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)
    return path


class TestInboundIntegration:
    def test_process_valid_orders(self, settings: Settings) -> None:
        store = InMemoryOrderStore()
        path = _place_order_file(Path(settings.paths.inbound_dir), [
            {
                "OrderID": "ORD-001", "OrderDate": "2026-03-30",
                "ArticleNumber": "SKU-001", "EAN": "4006381333931",
                "Quantity": "2", "NetPrice": "29.90", "Currency": "CHF",
                "CustomerReference": "REF-100", "DeliveryAddress": "Zurich",
            },
        ])
        result = process_order_file(path, settings, store)
        assert result["status"] == "processed"
        assert result["orders_saved"] == 1
        assert store.exists("ORD-001")

    def test_idempotent_reprocessing(self, settings: Settings) -> None:
        store = InMemoryOrderStore()

        # First process
        path1 = _place_order_file(Path(settings.paths.inbound_dir), [
            {
                "OrderID": "ORD-DUP", "OrderDate": "2026-03-30",
                "ArticleNumber": "SKU-001", "EAN": "",
                "Quantity": "1", "NetPrice": "10", "Currency": "CHF",
                "CustomerReference": "", "DeliveryAddress": "",
            },
        ], "ORDERS_20260330_100000.csv")
        result1 = process_order_file(path1, settings, store)
        assert result1["orders_saved"] == 1

        # Second process with same order ID
        path2 = _place_order_file(Path(settings.paths.inbound_dir), [
            {
                "OrderID": "ORD-DUP", "OrderDate": "2026-03-30",
                "ArticleNumber": "SKU-001", "EAN": "",
                "Quantity": "1", "NetPrice": "10", "Currency": "CHF",
                "CustomerReference": "", "DeliveryAddress": "",
            },
        ], "ORDERS_20260330_110000.csv")
        result2 = process_order_file(path2, settings, store)
        assert result2["orders_saved"] == 0
        assert result2["orders_skipped"] == 1

    def test_poll_and_process_end_to_end(self, settings: Settings, tmp_data_dir: Path) -> None:
        """End-to-end: place file on 'remote' sFTP → poll_and_process downloads, parses, saves."""
        transport = LocalClient(str(tmp_data_dir / "sftp_mock"))
        store = InMemoryOrderStore()

        # Place an order file directly in the remote inbound directory
        remote_inbound = Path(transport._base) / settings.sftp.remote_inbound_dir.lstrip("/")
        _place_order_file(remote_inbound, [
            {
                "OrderID": "ORD-E2E", "OrderDate": "2026-03-30",
                "ArticleNumber": "SKU-001", "EAN": "4006381333931",
                "Quantity": "3", "NetPrice": "29.90", "Currency": "CHF",
                "CustomerReference": "REF-E2E", "DeliveryAddress": "Bern",
            },
        ])

        results = poll_and_process(settings, transport, store)
        assert len(results) == 1
        assert results[0]["status"] == "processed"
        assert results[0]["orders_saved"] == 1
        assert store.exists("ORD-E2E")
