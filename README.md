# B2B Data Bridge

[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-78%20passing-brightgreen.svg)](#testing)

Automated B2B data exchange — bridges product, pricing, stock, and order data between e-commerce systems and distributors via CSV/XLSX files over sFTP.

Built for the Brack/Alltron integration pattern, but adaptable to any distributor that uses file-based data exchange.

## The Problem

B2B e-commerce partners often exchange data manually — exporting spreadsheets, uploading them to sFTP, downloading order files, and keying them into the ERP. This is slow, error-prone, and doesn't scale.

## The Solution

B2B Data Bridge automates both directions:

```
                        Outbound (you → distributor)
┌──────────────┐    ┌──────────────────┐    ┌──────────────┐
│  Your System │───▶│  B2B Data Bridge  │───▶│  Distributor  │
│  (products,  │    │  (validate, map,  │    │  sFTP server  │
│   pricing,   │    │   write CSV,      │    │  /outbound    │
│   stock)     │    │   upload)         │    └──────────────┘
└──────────────┘    └──────────────────┘

                        Inbound (distributor → you)
┌──────────────┐    ┌──────────────────┐    ┌──────────────┐
│  Distributor  │───▶│  B2B Data Bridge  │───▶│  Your System │
│  sFTP server  │    │  (download, parse, │    │  (orders     │
│  /inbound     │    │   validate, save)  │    │   ready)     │
└──────────────┘    └──────────────────┘    └──────────────┘
```

**Outbound** — takes your product catalogue, pricing, and stock levels, validates them, writes standardised CSV/XLSX files, and uploads to the distributor's sFTP server.

**Inbound** — downloads order files, parses and validates them, groups order lines into orders, deduplicates, and saves. Safe to re-run (idempotent).

## What Gets Exchanged

| Direction | File | Contents |
|-----------|------|----------|
| Outbound | `PRODUCTS_20260330_143000.csv` | SKU, name, EAN, description, category, brand, weight |
| Outbound | `PRICING_20260330_143000.csv` | SKU, net price, gross price, currency |
| Outbound | `STOCK_20260330_143000.csv` | SKU, available quantity, warehouse |
| Inbound | `ORDERS_20260330_100000.csv` | Order ID, date, SKU, quantity, price, currency, address |

All files use `;` as CSV delimiter (European standard), UTF-8 encoding, and follow strict naming conventions. See the [File Format Specification](docs/FILE_FORMAT_SPECIFICATION.md) for full schemas.

## Quick Start

### From Source

```bash
git clone https://github.com/YOUR_USERNAME/b2b-data-bridge.git
cd b2b-data-bridge
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

# Generate config files
b2b-data-bridge init

# Test locally (no sFTP needed)
b2b-data-bridge outbound --local
```

### Standalone Binary (No Python Required)

Download the latest release from [Releases](https://github.com/YOUR_USERNAME/b2b-data-bridge/releases), unzip, and run:

```bash
./b2b-data-bridge init                  # generate config files
# edit config/settings.yaml with your sFTP details
./b2b-data-bridge outbound --local      # dry run
./b2b-data-bridge outbound              # real sFTP upload
./b2b-data-bridge inbound               # download & process orders
```

## Project Structure

```
b2b-data-bridge/
├── config/settings.yaml          # Configuration (sFTP, paths, file format, naming)
├── src/b2b_data_bridge/
│   ├── config.py                 # YAML + .env settings loader
│   ├── models.py                 # Data models + mapping functions
│   ├── validation.py             # EAN check-digit (GS1), field validation
│   ├── files.py                  # CSV/XLSX read, write, archive
│   ├── sftp.py                   # sFTP client with retry + local dev fallback
│   ├── export.py                 # Outbound pipeline orchestration
│   ├── orders.py                 # Inbound pipeline orchestration
│   └── main.py                   # CLI entry point
├── tests/                        # 78 automated tests
├── samples/                      # Reference CSV files
│   ├── outbound/                 # PRODUCTS, PRICING, STOCK samples
│   └── inbound/                  # ORDERS sample
├── docs/                         # Full consulting documentation
└── pyproject.toml                # Project metadata + dependencies
```

## Configuration

All settings live in `config/settings.yaml`:

```yaml
sftp:
  host: sftp.distributor.example.com
  port: 22
  username: partner_user
  remote_outbound_dir: /outbound
  remote_inbound_dir: /inbound

paths:
  outbound_dir: ./data/outbound
  inbound_dir: ./data/inbound
  archive_dir: ./data/archive
  failed_dir: ./data/failed

files:
  default_format: csv
  csv_delimiter: ";"
  encoding: utf-8

retry:
  max_retries: 3
  base_delay: 2.0
  backoff_factor: 2.0
```

Sensitive values go in `.env` (never committed):

```
SFTP_HOST=sftp.distributor.example.com
SFTP_USERNAME=partner_user
SFTP_PASSWORD=your_password_here
```

## Built-in Safety

- **EAN/GTIN validation** — GS1 check-digit algorithm catches barcode typos before they reach the distributor
- **Required field checks** — SKU, name, price, quantity must be present and valid
- **Duplicate order detection** — idempotent processing; same order won't be saved twice
- **Bad file quarantine** — unparseable files moved to `data/failed/` with reason logged
- **sFTP retry with backoff** — transient failures retried automatically (3 attempts, exponential backoff, 5-min cap)
- **Path traversal protection** — prevents malicious filenames from escaping download directories
- **SSH host key verification** — RejectPolicy prevents man-in-the-middle attacks
- **Credential masking** — passwords never appear in logs or tracebacks

## Testing

```bash
pytest                                       # Run all 78 tests (< 1s)
pytest tests/test_validation.py -v           # Specific test file
pytest --cov=b2b_data_bridge                 # With coverage
```

## Documentation

| Document | Audience | Purpose |
|----------|----------|---------|
| [Architecture](docs/architecture.md) | Developers | System design, data flow diagrams, module responsibilities |
| [File Format Specification](docs/FILE_FORMAT_SPECIFICATION.md) | Both parties | Column schemas, validation rules, naming conventions — for sign-off |
| [sFTP Setup Guide](docs/SFTP_SETUP_GUIDE.md) | IT / Sysadmin | SSH keys, host verification, firewall rules, connectivity checklist |
| [Integration Test Plan](docs/INTEGRATION_TEST_PLAN.md) | QA / All parties | 12 UAT scenarios with pass/fail tracking |
| [Go-Live Runbook](docs/GO_LIVE_RUNBOOK.md) | Operations | Production deployment checklist, scheduling, monitoring, rollback |
| [Client Guide](docs/CLIENT_GUIDE.md) | End user | Non-technical quick start for running the tool |
| [Project Proposal](docs/PROJECT_PROPOSAL.md) | Business | Scope, phases, deliverables, risks, acceptance criteria |

## Connecting to Real Systems

The default installation uses sample data for outbound and an in-memory store for inbound orders. To connect to your actual systems:

**Outbound** — replace sample functions in `main.py`:

```python
def get_products():
    return your_erp.fetch_products()  # returns list[Product]
```

**Inbound** — replace `InMemoryOrderStore` with your database:

```python
class DatabaseOrderStore:
    def exists(self, order_id: str) -> bool:
        return db.query("SELECT 1 FROM orders WHERE id = ?", order_id)

    def save(self, order: Order) -> None:
        db.insert("orders", order.model_dump())
```

**Scheduling** via cron:

```bash
0 */2 * * *  cd /path/to/project && ./b2b-data-bridge outbound >> logs/cron.log 2>&1
*/15 * * * * cd /path/to/project && ./b2b-data-bridge inbound >> logs/cron.log 2>&1
```

## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on:

- Setting up the development environment
- Running tests
- Code style and conventions
- Submitting pull requests

## License

This project is licensed under the MIT License — see [LICENSE](LICENSE) for details.
