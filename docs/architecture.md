# B2B Data Bridge — Architecture

## Overview

The B2B Data Bridge automates the exchange of product, pricing, stock, and order data between an e-commerce company and its distributor (Brack/Alltron) via CSV/XLSX files over sFTP.

There are two pipelines:

- **Outbound** — push product catalogue, pricing, and stock updates to the distributor
- **Inbound** — receive and process orders from the distributor

---

## System Context

```mermaid
graph LR
    EC["E-Commerce System<br/>(Your shop / ERP)"]
    DI["B2B Data Bridge"]
    SFTP["sFTP Server<br/>(Brack/Alltron)"]

    EC -- "products, prices, stock" --> DI
    DI -- "CSV/XLSX files" --> SFTP
    SFTP -- "order CSV files" --> DI
    DI -- "parsed orders" --> EC
```

The bridge sits between your internal systems and the distributor's sFTP server. It handles all the file formatting, validation, transfer, and error handling.

---

## Module Structure

```mermaid
graph TB
    subgraph "b2b_data_bridge/"
        MAIN["main.py<br/>CLI entry point"]
        CONFIG["config.py<br/>YAML + .env settings"]
        MODELS["models.py<br/>Data models + mapping"]
        VALID["validation.py<br/>EAN, fields, filenames"]
        FILES["files.py<br/>CSV/XLSX read/write/archive"]
        SFTP["sftp.py<br/>sFTP client + retry"]
        EXPORT["export.py<br/>Outbound pipeline"]
        ORDERS["orders.py<br/>Inbound pipeline"]
    end

    MAIN --> CONFIG
    MAIN --> EXPORT
    MAIN --> ORDERS
    MAIN --> SFTP

    EXPORT --> MODELS
    EXPORT --> VALID
    EXPORT --> FILES

    ORDERS --> MODELS
    ORDERS --> VALID
    ORDERS --> FILES

    FILES --> CONFIG
    SFTP --> CONFIG
```

Each module has a clear, single responsibility:

| Module | Responsibility |
|--------|---------------|
| `config.py` | Load `settings.yaml`, apply `.env` overrides, provide typed config objects |
| `models.py` | Internal models (`Product`, `Price`, `Stock`, `Order`), external CSV row models, and mapping functions between them |
| `validation.py` | EAN check-digit (GS1), required-field checks, price/quantity validation, filename pattern validation, duplicate detection |
| `files.py` | Write CSV (`;`-delimited) and XLSX, parse them back, generate filenames (`PRODUCTS_20260330_143000.csv`), archive/quarantine processed files |
| `sftp.py` | Connect to sFTP, upload/download/list/remove files with automatic retry + exponential backoff. Includes a `LocalClient` for testing without a real server |
| `export.py` | Outbound orchestration: map → validate → write → upload → archive |
| `orders.py` | Inbound orchestration: download → parse → validate → group by OrderID → deduplicate against store → save → archive |
| `main.py` | CLI (`python -m b2b_data_bridge outbound|inbound`), loads config, wires everything together |

---

## Outbound Flow (Export)

This is triggered when you run `python -m b2b_data_bridge outbound`.

```mermaid
sequenceDiagram
    participant CLI as main.py
    participant EXP as export.py
    participant MOD as models.py
    participant VAL as validation.py
    participant FIL as files.py
    participant SFT as sftp.py

    CLI->>EXP: run_full_export(products, prices, stock)

    Note over EXP: For each data type (products, pricing, stock):

    EXP->>MOD: product_to_row(product)
    MOD-->>EXP: ExternalProductRow

    EXP->>VAL: validate_product_row(row, index)
    VAL-->>EXP: [] or [ValidationError, ...]

    alt Row has errors
        Note over EXP: Skip row, log warning
    end

    EXP->>FIL: make_filename("products", "csv", naming, ts)
    FIL-->>EXP: "PRODUCTS_20260330_143000.csv"

    EXP->>FIL: write_file(valid_rows, path, config)
    FIL-->>EXP: file path

    EXP->>SFT: upload(file_path, remote_outbound_dir)
    SFT-->>EXP: remote path

    EXP->>FIL: archive_file(file_path, archive_dir)
    FIL-->>EXP: archived path
```

**What the pipeline does, step by step:**

1. **Map** — converts internal `Product`/`Price`/`Stock` objects into flat `ExternalProductRow`/`ExternalPricingRow`/`ExternalStockRow` records (the CSV column format Brack/Alltron expects)
2. **Validate** — checks each row: required fields filled, EAN check-digit correct, prices > 0, quantities ≥ 0. Invalid rows are logged and skipped
3. **Write file** — generates a timestamped CSV (e.g. `PRODUCTS_20260330_143000.csv`) with `;` delimiter
4. **Upload** — sends the file to the distributor's sFTP server (with automatic retry on failure)
5. **Archive** — moves the local file into a date-stamped archive folder

**Example output file** (`PRODUCTS_20260330_143000.csv`):
```
ArticleNumber;ArticleName;EAN;Description;Category;Brand;WeightKG;LastUpdate
SKU-001;Wireless Mouse;4006381333931;Ergonomic wireless mouse;Peripherals;TechCorp;0.12;2026-03-30T10:00:00
SKU-002;USB-C Hub 7-Port;4006381333948;USB-C hub with 7 ports;Accessories;TechCorp;0.25;2026-03-30T10:00:00
```

---

## Inbound Flow (Orders)

This is triggered when you run `python -m b2b_data_bridge inbound`.

```mermaid
sequenceDiagram
    participant CLI as main.py
    participant ORD as orders.py
    participant SFT as sftp.py
    participant FIL as files.py
    participant VAL as validation.py
    participant MOD as models.py
    participant DB as OrderStore

    CLI->>ORD: poll_and_process(settings, transport, store)

    ORD->>SFT: list_files(remote_inbound_dir)
    SFT-->>ORD: ["/inbound/ORDERS_20260330_100000.csv"]

    loop For each remote file
        ORD->>SFT: download(remote_path, local_inbound_dir)
        SFT-->>ORD: local file path

        ORD->>VAL: validate_filename(name, "ORDERS", ext)
        alt Bad filename
            ORD->>FIL: quarantine_file(path, failed_dir)
            Note over ORD: Skip this file
        end

        ORD->>FIL: parse_file(path, ExternalOrderRow, config)
        FIL-->>ORD: rows, parse_errors

        ORD->>VAL: validate_order_row(row, index)
        VAL-->>ORD: errors per row

        ORD->>MOD: order_rows_to_orders(clean_rows)
        MOD-->>ORD: List[Order]

        loop For each order
            ORD->>DB: exists(order_id)?
            alt Already processed
                Note over ORD: Skip (idempotent)
            else New order
                ORD->>DB: save(order)
            end
        end

        ORD->>FIL: archive_file(path, archive_dir)
        ORD->>SFT: remove(remote_path)
    end
```

**What the pipeline does, step by step:**

1. **List** — checks the distributor's sFTP inbound folder for new order files
2. **Download** — pulls each file to the local inbound directory
3. **Validate filename** — must match pattern `ORDERS_YYYYMMDD_HHMMSS.csv`. Bad files → quarantine
4. **Parse** — reads CSV rows into typed `ExternalOrderRow` objects. Encoding/format errors → quarantine
5. **Validate rows** — checks each row: required fields, quantity ≥ 1, price > 0, valid currency
6. **Map** — groups rows by `OrderID` into `Order` objects with `OrderLine` items
7. **Save** — stores orders, skipping any already seen (idempotent reprocessing)
8. **Archive** — moves processed file to date-stamped archive, removes from sFTP

**Example inbound file** (`ORDERS_20260330_100000.csv`):
```
OrderID;OrderDate;ArticleNumber;EAN;Quantity;NetPrice;Currency;CustomerReference;DeliveryAddress
ORD-20260330-001;2026-03-30;SKU-001;4006381333931;2;29.90;CHF;CUST-REF-100;Bahnhofstrasse 1, 8001 Zurich
ORD-20260330-001;2026-03-30;SKU-003;4006381333955;1;89.00;CHF;CUST-REF-100;Bahnhofstrasse 1, 8001 Zurich
ORD-20260330-002;2026-03-30;SKU-002;4006381333948;5;49.90;CHF;CUST-REF-101;Marktgasse 12, 3011 Bern
```

Note how `ORD-20260330-001` appears twice — these are two line items for the same order. The system groups them into one `Order` with two `OrderLine` entries.

---

## Data Models

```mermaid
classDiagram
    class Product {
        +str sku
        +str name
        +str ean
        +str description
        +str category
        +str brand
        +Decimal weight_kg
        +datetime updated_at
    }

    class Price {
        +str sku
        +Decimal net_price
        +Decimal gross_price
        +str currency
        +int price_unit
        +datetime valid_from
        +datetime valid_to
    }

    class Stock {
        +str sku
        +int quantity
        +str warehouse
        +datetime updated_at
    }

    class Order {
        +str order_id
        +datetime order_date
        +str customer_ref
        +str delivery_address
        +List~OrderLine~ lines
    }

    class OrderLine {
        +str sku
        +str ean
        +int quantity
        +Decimal net_price
        +str currency
    }

    Order "1" --> "*" OrderLine : contains
```

**Internal models** (left side of the system) use proper Python types — `Decimal` for money, `int` for quantities, `datetime` for dates. Pydantic validates them on creation (e.g. price must be > 0, EAN must be 8–14 digits).

**External row models** (`ExternalProductRow`, `ExternalPricingRow`, etc.) are all-string representations matching the CSV column headers the distributor expects. The mapping functions convert between the two.

---

## File Naming Convention

All files follow the pattern:

```
{PREFIX}_{YYYYMMDD}_{HHMMSS}.{ext}
```

| Data type | Prefix | Example |
|-----------|--------|---------|
| Products  | `PRODUCTS` | `PRODUCTS_20260330_143000.csv` |
| Pricing   | `PRICING`  | `PRICING_20260330_143000.csv` |
| Stock     | `STOCK`    | `STOCK_20260330_143000.csv` |
| Orders    | `ORDERS`   | `ORDERS_20260330_100000.csv` |

Prefixes are configurable in `settings.yaml` under `naming`.

---

## Validation Rules

| Check | Applied to | Rule |
|-------|-----------|------|
| EAN check-digit | Products | GS1 algorithm, accepts EAN-8/12/13/14 |
| Required fields | All types | SKU, name, price, quantity, order ID must not be empty |
| Price > 0 | Pricing, Orders | Net price must be a positive number |
| Quantity ≥ 0 | Stock | Available quantity cannot be negative |
| Quantity ≥ 1 | Orders | Order line quantity must be at least 1 |
| Currency format | Pricing, Orders | Must be 3-letter uppercase ISO code (e.g. `CHF`, `EUR`) |
| Filename pattern | Inbound files | Must match `{PREFIX}_YYYYMMDD_HHMMSS.{ext}` |
| Duplicate orders | Inbound | Same `OrderID` within a file is flagged; across runs is skipped |

---

## Error Handling & Retry

```mermaid
graph TD
    A[sFTP operation] --> B{Success?}
    B -->|Yes| C[Continue pipeline]
    B -->|No| D{Retries left?}
    D -->|Yes| E["Wait (exponential backoff)"]
    E --> A
    D -->|No| F[Raise SftpError]
```

- **sFTP retry**: configurable max retries, base delay, and backoff factor (default: 3 retries, 2s base, 2x backoff → waits 2s, 4s, 8s)
- **Bad files**: quarantined to `data/failed/{date}/` with a log explaining why
- **Invalid rows**: skipped with warnings in the log, valid rows still processed
- **Duplicate orders**: silently skipped (idempotent — safe to re-run)

---

## Directory Layout at Runtime

```
data/
├── outbound/          ← generated files staged here before upload
├── inbound/           ← downloaded files land here for processing
├── archive/
│   └── 2026-03-30/    ← successfully processed files, by date
└── failed/
    └── 2026-03-30/    ← quarantined bad files, by date
```

---

## Configuration

All settings live in `config/settings.yaml`. Sensitive values (passwords) can be overridden via environment variables or a `.env` file.

```yaml
sftp:
  host: sftp.distributor.example.com
  port: 22
  username: partner_user
  remote_outbound_dir: /outbound
  remote_inbound_dir: /inbound

files:
  default_format: csv      # csv or xlsx
  csv_delimiter: ";"       # European standard

retry:
  max_retries: 3
  base_delay: 2.0
  backoff_factor: 2.0
```

Environment variable overrides: `SFTP_HOST`, `SFTP_PORT`, `SFTP_USERNAME`, `SFTP_PASSWORD`, `LOG_LEVEL`, `FILE_FORMAT`.

---

## Technology Choices

| Technology | Why |
|------------|-----|
| **Python 3.9+** | Widely available, good library ecosystem for file processing |
| **pydantic v2** | Data validation with clear error messages — catches bad data early |
| **paramiko** | Mature, well-tested sFTP library |
| **openpyxl** | Read/write Excel files when distributor requires XLSX |
| **PyYAML + python-dotenv** | Simple config management without overcomplicating things |
| **pytest** | 77 tests covering models, validation, file I/O, transport, and end-to-end flows |
