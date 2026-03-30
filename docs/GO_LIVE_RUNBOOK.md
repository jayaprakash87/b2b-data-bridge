# Go-Live Runbook

> **Purpose**: Step-by-step checklist for transitioning from testing to live production data exchange.  
> **Who runs this**: Integration Developer + Partner IT + Brack/Alltron contact  
> **When**: After all UAT test scenarios pass in Staging

---

## 1. Pre-Go-Live Checklist (T minus 1 week)

Complete **all** items before scheduling the go-live date:

### Configuration

- [ ] `config/settings.yaml` updated with **production** sFTP host, port, directories
- [ ] `.env` updated with **production** credentials
- [ ] Production SSH key pair generated and public key registered with Brack/Alltron
- [ ] Host key verified and added to `~/.ssh/known_hosts` on the production machine
- [ ] File format confirmed as `csv` (or `xlsx` if agreed with Brack/Alltron)
- [ ] `log_level` set to `INFO` (not `DEBUG` — avoids verbose output in production)

### Infrastructure

- [ ] Production machine identified (server, VM, or desktop that stays on)
- [ ] Python 3.9+ installed **OR** standalone binary deployed (no Python needed)
- [ ] Outbound connectivity to `sftp.brack.ch:22` confirmed from production machine
- [ ] Disk space sufficient for files + archives (estimate: 50 MB / month typical)
- [ ] Logs directory writable: `logs/`
- [ ] Data directories writable: `data/outbound`, `data/inbound`, `data/archive`, `data/failed`

### Data Source

- [ ] Real product data source connected (replace `_sample_products()` in `main.py` with DB/API call)
- [ ] Real pricing data source connected
- [ ] Real stock data source connected
- [ ] Order output destination defined (where do saved orders go — DB, ERP API, file?)

### Coordination

- [ ] Brack/Alltron notified of go-live date
- [ ] Brack/Alltron confirms staging tests passed on their side
- [ ] Emergency contact exchange: Partner IT phone + Brack/Alltron IT phone
- [ ] Agreed on support hours and response time for first 2 weeks

---

## 2. Go-Live Day Procedure

### Step 1: Final Staging Verification (30 min before)

```bash
# Point at staging, run one final round
./b2b-data-bridge outbound
./b2b-data-bridge inbound
```

Confirm: files uploaded, orders downloaded, no errors.

### Step 2: Switch to Production Config

```bash
# Back up staging config
cp config/settings.yaml config/settings.yaml.staging

# Apply production config (prepared during pre-go-live)
cp config/settings.yaml.production config/settings.yaml
cp .env.production .env
```

### Step 3: Verify Production Connectivity

```bash
# Quick manual sFTP test
sftp -i ./id_integration partner_acme@sftp.brack.ch
# At sftp> prompt:
ls /outbound
ls /inbound
exit
```

### Step 4: First Production Run (Outbound)

```bash
./b2b-data-bridge outbound
```

**Verify:**
- [ ] Console shows `[OK]` for products, pricing, stock
- [ ] Files appear on sFTP `/outbound`
- [ ] Brack/Alltron confirms receipt (call/email them)
- [ ] Local files archived in `data/archive/YYYY-MM-DD/`

### Step 5: First Production Run (Inbound)

```bash
./b2b-data-bridge inbound
```

**Verify:**
- [ ] Orders downloaded (if any available)
- [ ] Files removed from sFTP `/inbound` after processing
- [ ] Orders saved correctly
- [ ] No files in `data/failed/`

### Step 6: Enable Scheduling

Once manual runs succeed, set up automated scheduling:

**Linux/macOS (cron):**
```bash
crontab -e
# Add lines (adjust paths and schedule):
0 */2 * * * cd /path/to/b2b-data-bridge && ./b2b-data-bridge outbound >> logs/cron.log 2>&1
30 */2 * * * cd /path/to/b2b-data-bridge && ./b2b-data-bridge inbound >> logs/cron.log 2>&1
```

**Windows (Task Scheduler):**
- Create two tasks: "B2B Data Bridge Outbound" and "B2B Data Bridge Inbound"
- Trigger: every 2 hours (or as agreed)
- Program: path to `b2b-data-bridge.exe`
- Arguments: `outbound` or `inbound`
- Start in: the bundle directory

### Step 7: Confirm Automated Runs

- [ ] Wait for the next scheduled run
- [ ] Check `logs/` for successful execution
- [ ] Confirm files appear on sFTP and orders are processed

---

## 3. Post-Go-Live Monitoring (First 2 Weeks)

### Daily Checks

| Check | How | What to look for |
|-------|-----|-----------------|
| Logs healthy | Open `logs/` | No `ERROR` lines; `INFO` shows successful runs |
| Files archived | Check `data/archive/` | New date folders appearing daily |
| No quarantined files | Check `data/failed/` | Should be empty; investigate any files found |
| Orders flowing | Confirm with business team | Orders appearing in your system |
| Brack/Alltron happy | Email/call contact | No complaints about file format or missing data |

### Weekly Checks

| Check | How |
|-------|-----|
| Disk space | `du -sh data/` — archive grows over time |
| Log rotation | Ensure logs don't grow unbounded; consider adding `logrotate` |
| Archive cleanup | Old archives (30+ days) can be deleted or moved to cold storage |

---

## 4. Rollback Plan

If critical issues arise after go-live:

### Immediate (Stop the bleeding)

1. **Disable the scheduled jobs** (remove cron entries or disable Task Scheduler tasks)
2. **Notify Brack/Alltron** that automated exchange is paused
3. **Do NOT delete** any files in `data/archive/` or `data/failed/` (needed for investigation)

### Revert to Manual

If the integration cannot be fixed quickly:

1. Revert to manual CSV upload via sFTP GUI client (FileZilla, WinSCP)
2. Use the sample files in `samples/` as templates
3. Process inbound orders manually by downloading from sFTP

### Fix and Resume

1. Identify the issue from `logs/` and `data/failed/`
2. Fix the configuration or code
3. Test in staging first
4. Re-enable scheduling

---

## 5. Escalation Contacts

| Role | Name | Phone | Email |
|------|------|-------|-------|
| Integration Developer | | | |
| Partner IT Lead | | | |
| Brack/Alltron Technical Contact | | | |

---

## 6. Go-Live Sign-Off

| Milestone | Date | Confirmed By |
|-----------|------|-------------|
| Pre-go-live checklist complete | | |
| First outbound run successful | | |
| Brack/Alltron confirmed receipt | | |
| First inbound run successful | | |
| Scheduling enabled | | |
| 24-hour unattended run clean | | |
| **Go-live approved** | | |
