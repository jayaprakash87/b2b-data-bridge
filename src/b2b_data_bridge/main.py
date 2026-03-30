"""CLI entry point — run outbound export or inbound order processing.

Usage:
    b2b-data-bridge init               # generate settings.yaml in current dir
    b2b-data-bridge outbound           # export products, pricing, stock
    b2b-data-bridge inbound            # poll & process orders
    b2b-data-bridge outbound --local   # use local filesystem (no sFTP)
"""

from __future__ import annotations

import argparse
import logging
import logging.handlers
import sys
from decimal import Decimal
from pathlib import Path

from b2b_data_bridge.config import ConfigError, load_settings
from b2b_data_bridge.models import Price, Product, Stock
from b2b_data_bridge.sftp import LocalClient, SftpClient, SftpError

__version__ = "1.0.0"

_DEFAULT_SETTINGS = """\
# B2B Data Bridge — settings
# Edit this file to match your sFTP server and file preferences.

environment: production

sftp:
  host: sftp.distributor.example.com
  port: 22
  username: partner_user
  password: ""                     # or use SFTP_PASSWORD env var / .env file
  private_key_path: ""             # path to SSH private key (preferred over password)
  remote_outbound_dir: /outbound
  remote_inbound_dir: /inbound
  timeout: 30

paths:
  outbound_dir: ./data/outbound
  inbound_dir: ./data/inbound
  archive_dir: ./data/archive
  failed_dir: ./data/failed
  log_dir: ./logs

files:
  default_format: csv              # csv | xlsx
  encoding: utf-8
  csv_delimiter: ";"
  csv_quotechar: "\\""

naming:
  product_prefix: "PRODUCTS"
  pricing_prefix: "PRICING"
  stock_prefix: "STOCK"
  order_prefix: "ORDERS"
  timestamp_format: "%Y%m%d_%H%M%S"

retry:
  max_retries: 3
  base_delay: 2.0
  backoff_factor: 2.0

log_level: INFO
"""

_DEFAULT_ENV = """\
# sFTP credentials — keep this file secret, never commit to git
SFTP_HOST=sftp.distributor.example.com
SFTP_USERNAME=partner_user
SFTP_PASSWORD=your_password_here
SFTP_PRIVATE_KEY_PATH=
"""


def _setup_logging(level: str, log_dir: str | None = None) -> None:
    fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Always log to stderr
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stderr)]

    # Also write to a rotating file when a log directory is available
    if log_dir:
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            log_path / "b2b-data-bridge.log",
            maxBytes=10 * 1024 * 1024,  # 10 MB per file
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setFormatter(logging.Formatter(fmt))
        handlers.append(file_handler)

    logging.basicConfig(level=numeric_level, format=fmt, handlers=handlers)


# ---------------------------------------------------------------------------
# Sample data (replace with real DB/API calls)
# ---------------------------------------------------------------------------

def _sample_products() -> list[Product]:
    return [
        Product(sku="SKU-001", name="Wireless Mouse", ean="4006381333931",
                description="Ergonomic wireless mouse", category="Peripherals",
                brand="TechCorp", weight_kg=Decimal("0.12")),
        Product(sku="SKU-002", name="USB-C Hub", ean="4006381333948",
                description="7-port USB-C hub", category="Accessories",
                brand="TechCorp", weight_kg=Decimal("0.25")),
        Product(sku="SKU-003", name="Keyboard", ean="5901234123457",
                description="Mechanical keyboard", category="Peripherals",
                brand="KeyPro"),
        Product(sku="SKU-004", name="Monitor Stand", ean="4007249902122",
                description="Adjustable monitor stand", category="Furniture",
                brand="DeskWorks", weight_kg=Decimal("2.5")),
        Product(sku="SKU-005", name="Webcam HD", ean="8710103917083",
                description="1080p webcam", category="Peripherals",
                brand="VisionTech", weight_kg=Decimal("0.18")),
    ]


def _sample_prices() -> list[Price]:
    return [
        Price(sku="SKU-001", net_price=Decimal("29.90"), gross_price=Decimal("32.29"), currency="CHF"),
        Price(sku="SKU-002", net_price=Decimal("49.90"), gross_price=Decimal("53.89"), currency="CHF"),
        Price(sku="SKU-003", net_price=Decimal("89.00"), gross_price=Decimal("96.12"), currency="CHF"),
        Price(sku="SKU-004", net_price=Decimal("39.90"), gross_price=Decimal("43.09"), currency="CHF"),
        Price(sku="SKU-005", net_price=Decimal("59.90"), gross_price=Decimal("64.69"), currency="CHF"),
    ]


def _sample_stock() -> list[Stock]:
    return [
        Stock(sku="SKU-001", quantity=150, warehouse="WH-ZH"),
        Stock(sku="SKU-002", quantity=75, warehouse="WH-ZH"),
        Stock(sku="SKU-003", quantity=200, warehouse="WH-BE"),
        Stock(sku="SKU-004", quantity=50, warehouse="WH-ZH"),
        Stock(sku="SKU-005", quantity=120, warehouse="WH-BE"),
    ]


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_outbound(settings, transport) -> None:
    from b2b_data_bridge.export import run_full_export
    results = run_full_export(
        _sample_products(), _sample_prices(), _sample_stock(),
        settings, transport,
    )
    for r in results:
        status = "OK" if r["exported"] > 0 else "FAIL"
        print(f"  [{status}] {r['job_type']}: {r['exported']} rows exported, {r['errors']} errors")


def cmd_inbound(settings, transport) -> None:
    from b2b_data_bridge.orders import InMemoryOrderStore, poll_and_process
    store = InMemoryOrderStore()
    results = poll_and_process(settings, transport, store)
    if not results:
        print("  No inbound files found.")
        return
    for r in results:
        print(f"  [{r['status']}] {r['file']}: {r['orders_saved']} saved, {r.get('orders_skipped', 0)} skipped")


def cmd_init() -> None:
    """Generate starter config files in the current directory."""
    config_dir = Path("config")

    yaml_path = config_dir / "settings.yaml"
    if yaml_path.exists():
        print(f"  [SKIP] {yaml_path} already exists")
    else:
        config_dir.mkdir(parents=True, exist_ok=True)
        yaml_path.write_text(_DEFAULT_SETTINGS, encoding="utf-8")
        print(f"  [CREATED] {yaml_path}")

    env_path = Path(".env")
    if env_path.exists():
        print(f"  [SKIP] {env_path} already exists")
    else:
        env_path.write_text(_DEFAULT_ENV, encoding="utf-8")
        print(f"  [CREATED] {env_path}")

    print("\n  Next steps:")
    print("  1. Edit config/settings.yaml with your sFTP server details")
    print("  2. Edit .env with your sFTP password or key path")
    print("  3. Run: b2b-data-bridge outbound")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="B2B Data Bridge — B2B CSV/XLSX file exchange with distributors via sFTP",
    )
    parser.add_argument(
        "command", choices=["init", "outbound", "inbound"],
        help="init = generate config files | outbound = export data | inbound = import orders",
    )
    parser.add_argument("--config", default=None, help="Path to settings.yaml")
    parser.add_argument("--local", action="store_true", help="Use local filesystem instead of sFTP")
    parser.add_argument("--version", action="version", version=f"b2b-data-bridge {__version__}")
    args = parser.parse_args()

    if args.command == "init":
        print("\n=== B2B Data Bridge — INIT ===\n")
        cmd_init()
        print()
        return

    try:
        settings = load_settings(config_path=args.config)
    except ConfigError as exc:
        print(f"\n  [ERROR] Configuration: {exc}\n", file=sys.stderr)
        sys.exit(1)

    settings.paths.ensure_dirs()
    _setup_logging(settings.log_level, settings.paths.log_dir)

    if args.local:
        transport = LocalClient()
    else:
        transport = SftpClient(settings.sftp, settings.retry)

    print(f"\n=== B2B Data Bridge — {args.command.upper()} ===\n")

    try:
        if args.command == "outbound":
            if not args.local:
                with transport:
                    cmd_outbound(settings, transport)
            else:
                cmd_outbound(settings, transport)
        else:
            if not args.local:
                with transport:
                    cmd_inbound(settings, transport)
            else:
                cmd_inbound(settings, transport)
    except SftpError as exc:
        print(f"\n  [ERROR] sFTP: {exc}\n", file=sys.stderr)
        sys.exit(2)
    except KeyboardInterrupt:
        print("\n  Interrupted.\n")
        sys.exit(130)
    except Exception as exc:
        logging.getLogger(__name__).exception("Unexpected error")
        print(f"\n  [ERROR] Unexpected: {exc}\n", file=sys.stderr)
        sys.exit(3)

    print("\nDone.\n")


if __name__ == "__main__":
    main()
