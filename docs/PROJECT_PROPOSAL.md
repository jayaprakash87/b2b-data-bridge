# Project Proposal — B2B Data Integration for Brack/Alltron

> **Prepared for**: [Client Name]  
> **Prepared by**: [Your Name / Company]  
> **Date**: 30 March 2026  
> **Version**: 1.0

---

## 1. Executive Summary

[Client Name] needs to transition from manual spreadsheet exchange to automated electronic data integration with their distributor, Brack/Alltron. This involves bidirectional file exchange — sending product catalogues, pricing, and stock levels, and receiving purchase orders — via standardised CSV files over a secure sFTP connection.

This proposal covers the design, development, testing, and deployment of a lightweight integration tool that automates this entire process.

---

## 2. Scope of Work

### In Scope

| # | Deliverable | Description |
|---|-------------|-------------|
| 1 | **Integration Software** | Standalone tool that automates outbound (products, pricing, stock) and inbound (orders) data exchange |
| 2 | **File Format Specification** | Formal document defining CSV column schemas, naming conventions, encoding rules, validation rules — for sign-off by both parties |
| 3 | **sFTP Connectivity Setup** | SSH key generation, host key verification, firewall guidance, connection testing |
| 4 | **Integration Test Plan** | 12 UAT test scenarios covering all outbound/inbound flows, error cases, and edge cases |
| 5 | **Go-Live Runbook** | Step-by-step production deployment checklist, scheduling setup, monitoring guide, rollback plan |
| 6 | **Sample Files** | Reference CSV files for products, pricing, stock, and orders |
| 7 | **Client Guide** | Non-technical guide for the person who runs the tool daily |
| 8 | **UAT Support** | Assistance during user acceptance testing in staging environment |
| 9 | **Go-Live Support** | Hands-on support during the production go-live day |

### Out of Scope

| Item | Reason |
|------|--------|
| ERP/database integration | Client's internal data source integration is separate. The tool currently uses sample data — connecting to the real DB/API is a separate phase. |
| Brack/Alltron server setup | The sFTP server is managed by Brack/Alltron. We configure our side. |
| Ongoing maintenance | Post-go-live maintenance and support can be covered under a separate retainer (see §6). |
| Custom UI/dashboard | The tool runs via command line and cron. A web dashboard is not in scope. |

---

## 3. Technical Approach

### Architecture

```
    Partner's System                              Brack/Alltron
    ────────────────                              ──────────────
                         ┌──────────────────┐
    Products/Prices ──→  │                  │  ──→  sFTP /outbound
    Stock Levels    ──→  │  B2B Data Bridge │  ──→  (CSV files)
                         │                  │
                         │  (validate,      │
                         │   map, export,   │
    Order Processing ←── │   import)        │  ←──  sFTP /inbound
                         └──────────────────┘       (order CSVs)
```

### Technology

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Language | Python 3.9+ | Widely supported, simple to maintain |
| Delivery | Standalone binary (no Python install needed) | Zero-dependency deployment for the client |
| File format | CSV with `;` delimiter | Swiss/European standard, required by Brack/Alltron |
| Transport | sFTP over SSH | Encrypted, required by Brack/Alltron |
| Scheduling | OS-native (cron / Task Scheduler) | No extra infrastructure needed |
| Configuration | YAML + environment variables | Separate config from code; secrets in `.env` |

### Security

- SSH host key verification (prevents man-in-the-middle)
- SSH key authentication (preferred over passwords)
- Credentials stored in `.env`, never in code or YAML
- Input validation on all incoming files
- Path traversal protection on file downloads
- Row count limits to prevent memory exhaustion

---

## 4. Project Phases

### Phase 1 — Setup & Development (Completed)

| Task | Status |
|------|--------|
| Develop integration tool (8 modules) | ✅ Done |
| 78 automated unit/integration tests | ✅ Done |
| File format specification | ✅ Done |
| Sample files for all data types | ✅ Done |
| Security audit (OWASP top 10) | ✅ Done |
| Standalone binary build | ✅ Done |

### Phase 2 — sFTP Setup & Connectivity

| Task | Owner | Duration |
|------|-------|----------|
| Obtain sFTP credentials from Brack/Alltron | Client | 1–3 days |
| Generate SSH key pair | Developer | 1 hour |
| Exchange keys with Brack/Alltron | Client + Brack/Alltron | 1–2 days |
| Verify firewall / network access | Client IT | 1 day |
| Run connectivity checklist (10 steps) | Developer | 1 hour |

### Phase 3 — Staging & UAT

| Task | Owner | Duration |
|------|-------|----------|
| Deploy tool on client's staging machine | Developer | 2 hours |
| Connect to real data source (DB/API) | Developer + Client | 1–2 days |
| Run 12 UAT test scenarios | Developer + Client | 1 day |
| Brack/Alltron validates received files | Brack/Alltron | 1–2 days |
| Fix any issues found | Developer | As needed |
| UAT sign-off | All parties | — |

### Phase 4 — Go-Live

| Task | Owner | Duration |
|------|-------|----------|
| Switch config to production | Developer | 30 minutes |
| First production outbound run | Developer | 15 minutes |
| Brack/Alltron confirms receipt | Brack/Alltron | 1 hour |
| First production inbound run | Developer | 15 minutes |
| Set up automated scheduling (cron) | Developer | 30 minutes |
| Monitor for 24 hours unattended | Developer | 1 day |
| Go-live sign-off | All parties | — |

### Phase 5 — Hypercare (First 2 Weeks)

| Task | Owner |
|------|-------|
| Daily log review | Developer |
| Respond to issues within 4 business hours | Developer |
| Weekly check-in call with Client | Developer + Client |
| Handover to Client IT for routine monitoring | Developer |

---

## 5. Deliverables Summary

| # | Deliverable | Format |
|---|-------------|--------|
| 1 | Integration tool | Standalone binary (macOS/Windows/Linux) |
| 2 | Source code | Python, fully tested, Git repository |
| 3 | File Format Specification | Markdown (printable) |
| 4 | sFTP Setup Guide | Markdown |
| 5 | Integration Test Plan | Markdown (with checkboxes) |
| 6 | Go-Live Runbook | Markdown |
| 7 | Client Quick Start Guide | Markdown |
| 8 | Architecture Documentation | Markdown with diagrams |
| 9 | Sample CSV files | `samples/outbound/` + `samples/inbound/` |
| 10 | Configuration templates | `settings.yaml` + `.env.example` |

---

## 6. Post-Project Support (Optional)

Available under a separate retainer agreement:

| Service | Description |
|---------|-------------|
| **Bug fixes** | Fix issues discovered after go-live |
| **Format changes** | Update CSV schemas if Brack/Alltron changes requirements |
| **New data types** | Add new file types (e.g. returns, shipment confirmations) |
| **Monitoring** | Set up alerting (email on failure) |
| **Cross-platform builds** | Build Windows `.exe` if client runs on Windows |

---

## 7. Assumptions & Dependencies

| # | Assumption |
|---|-----------|
| 1 | Brack/Alltron provides sFTP credentials and staging environment access |
| 2 | Client provides access to their product/pricing/stock data source (DB or API) |
| 3 | Client has a machine that can run scheduled tasks (always-on server, VM, or desktop) |
| 4 | CSV file format (columns, delimiter, encoding) is as documented in the File Format Specification |
| 5 | Brack/Alltron's sFTP server is available for testing during business hours |
| 6 | Network/firewall changes can be requested and implemented within 2 business days |

---

## 8. Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| sFTP credentials delayed by Brack/Alltron | Blocks Phase 2 | Medium | Request early; use `--local` mode for parallel development |
| Brack/Alltron changes file format after spec sign-off | Rework CSV schemas | Low | Formal sign-off on File Format Specification before development |
| Client's data source not accessible via API | Can't connect real data | Medium | Clarify data access method in Phase 2; may need custom adapter |
| Firewall blocks port 22 | Connectivity fails | Low | Test early in Phase 2; escalate to network team immediately |
| Client staff unavailable for UAT | Delays go-live | Medium | Schedule UAT date during Phase 1; reserve calendar |

---

## 9. Acceptance

This proposal is accepted by:

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Client Representative | | | |
| Developer / Freelancer | | | |
