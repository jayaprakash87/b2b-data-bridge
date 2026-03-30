# Integration Test Plan — UAT Scenarios

> **Version**: 1.0  
> **Date**: 30 March 2026  
> **Purpose**: Verify end-to-end data integration between Partner and Brack/Alltron before go-live.  
> **Testers**: Partner IT + Brack/Alltron Technical Contact

---

## 1. Test Environments

| Environment | Purpose | sFTP Host | Status |
|-------------|---------|-----------|--------|
| **Local** | Developer testing (no real sFTP) | `--local` flag | Available now |
| **Staging** | Test against Brack/Alltron staging server | TBD by Brack/Alltron | Pending setup |
| **Production** | Live data exchange | `sftp.brack.ch` | After UAT sign-off |

All tests below should be executed first in Local, then repeated in Staging.

---

## 2. Pre-Test Checklist

Before running any test scenario, confirm:

- [ ] `config/settings.yaml` points to the correct environment
- [ ] `.env` has valid credentials for the target environment
- [ ] sFTP connectivity verified (all 10 checks from sFTP Setup Guide pass)
- [ ] `data/` directories exist (run `b2b-data-bridge init` if needed)
- [ ] Sample files are available in `samples/`

---

## 3. Test Scenarios

### TC-01: Outbound — Product Catalogue Export

| Field | Detail |
|-------|--------|
| **Objective** | Export product catalogue CSV and verify it lands on the sFTP server |
| **Precondition** | Product data available; sFTP connection working |
| **Steps** | 1. Run `./b2b-data-bridge outbound`<br/>2. Check sFTP `/outbound` directory<br/>3. Download the generated `PRODUCTS_*.csv`<br/>4. Open in Excel/text editor |
| **Expected** | File exists on sFTP with correct name pattern. Header row matches spec. All mandatory fields populated. EAN values pass check-digit. `;` delimiter. UTF-8 encoding. |
| **Result** | ☐ Pass ☐ Fail |
| **Notes** | |

### TC-02: Outbound — Pricing Export

| Field | Detail |
|-------|--------|
| **Objective** | Export pricing CSV with correct prices and currency |
| **Steps** | 1. Run `./b2b-data-bridge outbound`<br/>2. Download `PRICING_*.csv` from sFTP `/outbound` |
| **Expected** | `NetPrice` > 0, `Currency` = valid ISO code (e.g. `CHF`), `ArticleNumber` matches product catalogue |
| **Result** | ☐ Pass ☐ Fail |
| **Notes** | |

### TC-03: Outbound — Stock Levels Export

| Field | Detail |
|-------|--------|
| **Objective** | Export stock CSV with correct quantities |
| **Steps** | 1. Run `./b2b-data-bridge outbound`<br/>2. Download `STOCK_*.csv` from sFTP `/outbound` |
| **Expected** | `AvailableQty` ≥ 0, `ArticleNumber` matches product catalogue |
| **Result** | ☐ Pass ☐ Fail |
| **Notes** | |

### TC-04: Outbound — Validation (Invalid Rows Skipped)

| Field | Detail |
|-------|--------|
| **Objective** | Verify that rows with invalid data are skipped, not exported |
| **Steps** | 1. Add a product with an invalid EAN (bad check digit)<br/>2. Run outbound export<br/>3. Check output CSV |
| **Expected** | Invalid product is NOT in the CSV. Log shows "validation errors — skipped those rows". Valid rows are still exported. |
| **Result** | ☐ Pass ☐ Fail |
| **Notes** | |

### TC-05: Outbound — Local Dry Run

| Field | Detail |
|-------|--------|
| **Objective** | Confirm `--local` mode writes files to disk without touching sFTP |
| **Steps** | 1. Run `./b2b-data-bridge outbound --local`<br/>2. Check `data/archive/` for today's date folder<br/>3. Confirm no files on sFTP |
| **Expected** | Files written locally and archived. No sFTP connection attempted. |
| **Result** | ☐ Pass ☐ Fail |
| **Notes** | |

---

### TC-06: Inbound — Process Valid Order File

| Field | Detail |
|-------|--------|
| **Objective** | Download and process a valid order CSV from sFTP |
| **Precondition** | Place `samples/inbound/ORDERS_sample.csv` on sFTP `/inbound` (rename to `ORDERS_20260330_100000.csv`) |
| **Steps** | 1. Upload sample order file to sFTP `/inbound`<br/>2. Run `./b2b-data-bridge inbound`<br/>3. Check console output |
| **Expected** | Orders saved. File removed from sFTP `/inbound`. File moved to `data/archive/`. |
| **Result** | ☐ Pass ☐ Fail |
| **Notes** | |

### TC-07: Inbound — Multi-Line Order

| Field | Detail |
|-------|--------|
| **Objective** | Verify that multiple CSV rows with the same `OrderID` are grouped into one order |
| **Precondition** | Order file contains 2+ rows with OrderID `ORD-20260330-001` |
| **Steps** | 1. Upload the sample file (which has 2 lines for ORD-20260330-001)<br/>2. Run inbound |
| **Expected** | Console shows `1` order saved for ORD-20260330-001 (not 2). The order contains 2 line items. |
| **Result** | ☐ Pass ☐ Fail |
| **Notes** | |

### TC-08: Inbound — Duplicate Order (Idempotency)

| Field | Detail |
|-------|--------|
| **Objective** | Re-processing the same order file does not create duplicate orders |
| **Steps** | 1. Place same order file on sFTP again<br/>2. Run inbound a second time |
| **Expected** | Console shows `0 saved, N skipped`. No duplicate entries. |
| **Result** | ☐ Pass ☐ Fail |
| **Notes** | |

### TC-09: Inbound — Bad Filename Quarantine

| Field | Detail |
|-------|--------|
| **Objective** | Files with non-standard names are quarantined, not processed |
| **Steps** | 1. Upload a file named `random_orders.csv` to sFTP `/inbound`<br/>2. Run inbound |
| **Expected** | File moved to `data/failed/`. Console shows "quarantined". Other valid files still processed. |
| **Result** | ☐ Pass ☐ Fail |
| **Notes** | |

### TC-10: Inbound — Corrupt File Quarantine

| Field | Detail |
|-------|--------|
| **Objective** | Corrupt/unreadable files don't crash the system |
| **Steps** | 1. Upload a binary/garbage file named `ORDERS_20260330_120000.csv` to sFTP<br/>2. Run inbound |
| **Expected** | File quarantined. Error logged. System continues processing other files. |
| **Result** | ☐ Pass ☐ Fail |
| **Notes** | |

---

### TC-11: Error Recovery — sFTP Disconnection

| Field | Detail |
|-------|--------|
| **Objective** | System retries on transient sFTP failures |
| **Steps** | 1. Start an outbound export<br/>2. Observe retry behaviour in logs if connection drops |
| **Expected** | System retries up to 3 times with exponential backoff. Clear error message if all retries fail. |
| **Result** | ☐ Pass ☐ Fail |
| **Notes** | Difficult to test without simulating failure. Verify via code review or by pointing at an unreachable host. |

### TC-12: Error Recovery — Bad Config

| Field | Detail |
|-------|--------|
| **Objective** | Invalid configuration produces a clear error, not a crash |
| **Steps** | 1. Corrupt `settings.yaml` (e.g. add `{{invalid`)<br/>2. Run any command |
| **Expected** | Clean error message: `[ERROR] Configuration: Invalid YAML in ...`. Exit code 1. No Python traceback. |
| **Result** | ☐ Pass ☐ Fail |
| **Notes** | |

---

## 4. Acceptance Criteria

The integration is ready for go-live when **all** of the following are true:

- [ ] TC-01 through TC-03 pass in **Staging** environment (real sFTP)
- [ ] Brack/Alltron confirms they can read and process the uploaded files
- [ ] TC-06 through TC-08 pass with order files provided by Brack/Alltron
- [ ] No data loss: all valid rows exported, all valid orders imported
- [ ] Invalid data is skipped cleanly without crashing
- [ ] File archiving works (processed files in `data/archive/`, failures in `data/failed/`)
- [ ] Scheduling (cron / Task Scheduler) runs unattended for 24+ hours

---

## 5. Test Results Summary

| Test | Local | Staging | Notes |
|------|-------|---------|-------|
| TC-01 Product export | ☐ | ☐ | |
| TC-02 Pricing export | ☐ | ☐ | |
| TC-03 Stock export | ☐ | ☐ | |
| TC-04 Validation skip | ☐ | ☐ | |
| TC-05 Local dry run | ☐ | ☐ | |
| TC-06 Valid orders | ☐ | ☐ | |
| TC-07 Multi-line order | ☐ | ☐ | |
| TC-08 Idempotency | ☐ | ☐ | |
| TC-09 Bad filename | ☐ | ☐ | |
| TC-10 Corrupt file | ☐ | ☐ | |
| TC-11 sFTP retry | ☐ | ☐ | |
| TC-12 Bad config | ☐ | ☐ | |

**Sign-off:**

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Partner (Client) | | | |
| Brack/Alltron | | | |
| Integration Developer | | | |
