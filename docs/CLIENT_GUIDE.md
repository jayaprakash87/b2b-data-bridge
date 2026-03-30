# B2B Data Bridge — Quick Start Guide

> This guide is for the person who will run the tool. No programming knowledge needed.

---

## What This Tool Does

The B2B Data Bridge automatically exchanges files with your distributor (Brack/Alltron):

- **Outbound**: Sends your product catalogue, pricing, and stock levels as CSV files to the distributor's sFTP server
- **Inbound**: Downloads new orders from the distributor's sFTP server and saves them locally

```
    Your System                          Distributor
    ──────────                          ───────────
    Products  ──┐
    Pricing   ──┼──→  CSV files ──→  sFTP Server
    Stock     ──┘
                    
                     Order CSVs  ←──  sFTP Server
```

---

## Setup (One Time)

### Step 1: Unzip

Unzip the `b2b-data-bridge-bundle.zip` you received. You'll see:

```
b2b-data-bridge-bundle/
├── b2b-data-bridge          ← the program (double-click won't work, use terminal)
├── config/
│   └── settings.yaml        ← YOUR SETTINGS — edit this
├── .env.example              ← copy to .env for passwords
└── samples/                  ← example CSV files for reference
```

### Step 2: Configure

Open `config/settings.yaml` in any text editor (Notepad, TextEdit, etc.) and fill in your real values:

```yaml
sftp:
  host: sftp.brack.ch              # ← your actual sFTP server address
  port: 22
  username: your_username           # ← your sFTP username
  private_key_path: ./id_rsa        # ← path to your SSH key file
  remote_outbound_dir: /outbound    # ← where to upload files
  remote_inbound_dir: /inbound      # ← where to download orders from
```

### Step 3: Set Password (if not using SSH key)

Copy `.env.example` to `.env` and edit it:

```
SFTP_PASSWORD=your_actual_password
```

> **Security**: The `.env` file contains your password. Never share or email it.

### Step 4: Add Host Key

Before the first connection, add the server's SSH fingerprint to your known hosts:

```bash
ssh-keyscan -p 22 sftp.brack.ch >> ~/.ssh/known_hosts
```

---

## Running the Tool

Open **Terminal** (Mac/Linux) or **Command Prompt** (Windows). Navigate to the unzipped folder:

```bash
cd path/to/b2b-data-bridge-bundle
```

### Send data to distributor (outbound)

```bash
./b2b-data-bridge outbound
```

You'll see output like:

```
=== B2B Data Bridge — OUTBOUND ===

  [OK] products: 5 rows exported, 0 errors
  [OK] pricing: 5 rows exported, 0 errors
  [OK] stock: 5 rows exported, 0 errors

Done.
```

### Receive orders from distributor (inbound)

```bash
./b2b-data-bridge inbound
```

### Test without real sFTP (dry run)

```bash
./b2b-data-bridge outbound --local
```

This writes files to your local disk only — nothing is uploaded.

---

## Scheduling (Run Automatically)

### Mac/Linux (cron)

Run every hour:

```bash
crontab -e
```

Add this line:

```
0 * * * * cd /path/to/b2b-data-bridge-bundle && ./b2b-data-bridge outbound >> logs/cron.log 2>&1
```

### Windows (Task Scheduler)

1. Open **Task Scheduler**
2. Create Basic Task → name it "B2B Data Bridge Export"
3. Trigger: Daily / Hourly (your choice)
4. Action: Start a Program
   - Program: `C:\path\to\b2b-data-bridge-bundle\b2b-data-bridge.exe`
   - Arguments: `outbound`
   - Start in: `C:\path\to\b2b-data-bridge-bundle`

---

## File Locations

After running, you'll find:

| Folder | What's in it |
|--------|-------------|
| `data/outbound/` | Temporarily holds files before upload (auto-cleaned) |
| `data/inbound/` | Downloaded order files (auto-moved after processing) |
| `data/archive/` | Successfully processed files, organized by date |
| `data/failed/` | Files that had errors — check these if something goes wrong |
| `logs/` | Activity logs |

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "No such file: settings.yaml" | Run `./b2b-data-bridge init` to generate default config |
| "sFTP connected" but nothing uploads | Check `remote_outbound_dir` in settings.yaml matches the server |
| "Host key verification failed" | Run `ssh-keyscan -p 22 YOUR_HOST >> ~/.ssh/known_hosts` |
| Files show in `data/failed/` | Open the file — the filename may not match the expected pattern |
| "Permission denied" on Mac | Run `chmod +x ./b2b-data-bridge` once |

---

## Getting Help

Contact your developer if you encounter issues not listed above.
Include the contents of `logs/` when reporting problems.
