# File Format Specification — Interface Control Document (ICD)

> **Version**: 1.0  
> **Date**: 30 March 2026  
> **Parties**: Partner (Client) ↔ Brack/Alltron (Distributor)  
> **Status**: Draft — pending sign-off by both parties

---

## 1. General Rules

All files exchanged between Partner and Brack/Alltron follow these rules:

| Rule | Value |
|------|-------|
| File format | CSV (default) or XLSX |
| Encoding | **UTF-8** (with or without BOM) |
| CSV delimiter | `;` (semicolon) |
| CSV quote character | `"` (double quote) |
| Line ending | `\r\n` (Windows) or `\n` (Unix) — both accepted |
| Header row | **Required** — first row contains column names exactly as specified below |
| Date format | `YYYY-MM-DDTHH:MM:SS` (ISO 8601) or `YYYY-MM-DD` |
| Decimal separator | `.` (dot) — e.g. `29.90`, not `29,90` |
| Currency | ISO 4217 3-letter code (e.g. `CHF`, `EUR`) |
| Empty optional fields | Leave blank (no placeholder text) |

### Filename Convention

All filenames follow the pattern:

```
{PREFIX}_{YYYYMMDD}_{HHMMSS}.{ext}
```

| Component | Description | Example |
|-----------|-------------|---------|
| PREFIX | File type identifier (see below) | `PRODUCTS` |
| YYYYMMDD | Date of generation | `20260330` |
| HHMMSS | Time of generation | `143000` |
| ext | File extension | `csv` or `xlsx` |

**Example**: `PRODUCTS_20260330_143000.csv`

Files not matching this pattern will be **rejected** by the system.

---

## 2. Outbound Files (Partner → Brack/Alltron)

These files are **uploaded by the Partner** to the distributor's sFTP server.

### 2.1 Product Catalogue — `PRODUCTS_*.csv`

Contains the Partner's full product catalogue. Sent whenever products are added or updated.

| Column | Type | Mandatory | Description | Example |
|--------|------|-----------|-------------|---------|
| `ArticleNumber` | String | **Yes** | Partner's unique product SKU | `SKU-001` |
| `ArticleName` | String | **Yes** | Product display name | `Wireless Mouse` |
| `EAN` | String (8–14 digits) | **Yes** | EAN/GTIN barcode. Must pass GS1 check-digit validation | `4006381333931` |
| `Description` | String | No | Product description | `Ergonomic wireless mouse` |
| `Category` | String | No | Product category | `Peripherals` |
| `Brand` | String | No | Brand name | `TechCorp` |
| `WeightKG` | Decimal | No | Weight in kilograms | `0.12` |
| `LastUpdate` | DateTime | No | When this record was last changed | `2026-03-30T10:00:00` |

**Validation rules:**
- `ArticleNumber` and `ArticleName` must not be empty
- `EAN` must be a valid EAN-8, EAN-12, EAN-13, or EAN-14 with correct GS1 check digit
- Rows failing validation are skipped (not included in the file)

**Sample file:**
```
ArticleNumber;ArticleName;EAN;Description;Category;Brand;WeightKG;LastUpdate
SKU-001;Wireless Mouse;4006381333931;Ergonomic wireless mouse;Peripherals;TechCorp;0.12;2026-03-30T10:00:00
SKU-002;USB-C Hub 7-Port;4006381333948;USB-C hub with 7 ports;Accessories;TechCorp;0.25;2026-03-30T10:00:00
```

---

### 2.2 Price List — `PRICING_*.csv`

Contains current pricing for all active products.

| Column | Type | Mandatory | Description | Example |
|--------|------|-----------|-------------|---------|
| `ArticleNumber` | String | **Yes** | Must match a `ArticleNumber` in the product file | `SKU-001` |
| `NetPrice` | Decimal | **Yes** | Net price (excl. VAT). Must be > 0 | `29.90` |
| `GrossPrice` | Decimal | No | Gross price (incl. VAT) | `32.29` |
| `Currency` | String (3 chars) | **Yes** | ISO 4217 currency code | `CHF` |
| `PriceUnit` | Integer | No | Price per N units (default: 1) | `1` |
| `ValidFrom` | DateTime | No | Price effective start date | `2026-04-01T00:00:00` |
| `ValidTo` | DateTime | No | Price effective end date | `2026-06-30T23:59:59` |

**Validation rules:**
- `NetPrice` must be a positive decimal number
- `Currency` must be exactly 3 uppercase letters (ISO 4217)

**Sample file:**
```
ArticleNumber;NetPrice;GrossPrice;Currency;PriceUnit;ValidFrom;ValidTo
SKU-001;29.90;32.29;CHF;1;;
SKU-002;49.90;53.89;CHF;1;;
```

---

### 2.3 Stock Levels — `STOCK_*.csv`

Contains current stock availability.

| Column | Type | Mandatory | Description | Example |
|--------|------|-----------|-------------|---------|
| `ArticleNumber` | String | **Yes** | Must match a `ArticleNumber` in the product file | `SKU-001` |
| `AvailableQty` | Integer | **Yes** | Number of units in stock. Must be ≥ 0 | `150` |
| `Warehouse` | String | No | Warehouse identifier | `WH-ZH` |
| `RestockDate` | DateTime | No | Expected restock date (if out of stock) | `2026-04-15T00:00:00` |
| `LastUpdate` | DateTime | No | When stock count was last checked | `2026-03-30T10:00:00` |

**Validation rules:**
- `AvailableQty` must be a non-negative integer

**Sample file:**
```
ArticleNumber;AvailableQty;Warehouse;RestockDate;LastUpdate
SKU-001;150;WH-ZH;;2026-03-30T10:00:00
SKU-002;75;WH-ZH;;2026-03-30T10:00:00
SKU-003;0;WH-BE;2026-04-15T00:00:00;2026-03-30T10:00:00
```

---

## 3. Inbound Files (Brack/Alltron → Partner)

These files are **placed by the distributor** on the sFTP server for the Partner to download.

### 3.1 Orders — `ORDERS_*.csv`

Contains purchase orders. Each row is one order line (one product within an order). Multiple rows with the same `OrderID` represent multi-item orders.

| Column | Type | Mandatory | Description | Example |
|--------|------|-----------|-------------|---------|
| `OrderID` | String | **Yes** | Unique order identifier | `ORD-20260330-001` |
| `OrderDate` | DateTime | **Yes** | When the order was placed | `2026-03-30` |
| `ArticleNumber` | String | **Yes** | SKU of the ordered product | `SKU-001` |
| `EAN` | String | No | EAN/GTIN of the product | `4006381333931` |
| `Quantity` | Integer | **Yes** | Number of units ordered. Must be ≥ 1 | `2` |
| `NetPrice` | Decimal | **Yes** | Net price per unit. Must be > 0 | `29.90` |
| `Currency` | String (3 chars) | **Yes** | ISO 4217 currency code | `CHF` |
| `CustomerReference` | String | No | Buyer's reference number | `CUST-REF-100` |
| `DeliveryAddress` | String | No | Shipping address | `Bahnhofstrasse 1, 8001 Zurich` |

**Validation rules:**
- `OrderID`, `ArticleNumber` must not be empty
- `Quantity` must be ≥ 1
- `NetPrice` must be > 0
- `Currency` must be 3 uppercase letters
- Duplicate `OrderID`s across files are handled via idempotent processing (re-sent orders are skipped)

**Sample file (multi-line order):**
```
OrderID;OrderDate;ArticleNumber;EAN;Quantity;NetPrice;Currency;CustomerReference;DeliveryAddress
ORD-20260330-001;2026-03-30;SKU-001;4006381333931;2;29.90;CHF;CUST-REF-100;Bahnhofstrasse 1, 8001 Zurich
ORD-20260330-001;2026-03-30;SKU-003;4006381333955;1;89.00;CHF;CUST-REF-100;Bahnhofstrasse 1, 8001 Zurich
ORD-20260330-002;2026-03-30;SKU-002;4006381333948;5;49.90;CHF;CUST-REF-101;Marktgasse 12, 3011 Bern
```

Here, `ORD-20260330-001` has two line items (mouse + keyboard). The system groups these into a single order with two lines.

---

## 4. EAN/GTIN Check-Digit Algorithm

All EAN/GTIN values are validated using the **GS1 standard check-digit algorithm**:

1. Take all digits except the last (the check digit)
2. From the **rightmost**, alternately multiply by **1** and **3**
3. Sum all results
4. Check digit = `(10 - (sum % 10)) % 10`
5. Compare with the last digit of the EAN

**Example** for EAN-13 `4006381333931`:
- Digits: `4 0 0 6 3 8 1 3 3 3 9 3` → check digit: `1`
- Weighted sum: `4×1 + 0×3 + 0×1 + 6×3 + 3×1 + 8×3 + 1×1 + 3×3 + 3×1 + 3×3 + 9×1 + 3×3 = 89`
- `(10 - (89 % 10)) % 10 = 1` ✓

---

## 5. Error Handling

| Scenario | Behaviour |
|----------|-----------|
| File with bad filename pattern | Rejected, moved to quarantine folder |
| Row with missing mandatory field | Row skipped, rest of file processed |
| Row with invalid EAN check-digit | Row skipped, logged as validation error |
| Row with invalid price/quantity | Row skipped, logged |
| File parse error (bad encoding, corrupt file) | Entire file quarantined |
| Duplicate order (same OrderID already processed) | Silently skipped (idempotent) |
| sFTP connection failure | Automatic retry with exponential backoff (3 attempts) |

---

## 6. Sign-Off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Partner (Client) | | | |
| Brack/Alltron Technical Contact | | | |
| Integration Developer | | | |
