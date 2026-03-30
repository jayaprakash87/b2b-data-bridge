# sFTP Connectivity Setup Guide

> **Purpose**: Step-by-step instructions for establishing the secure sFTP connection between Partner and Brack/Alltron.  
> **Audience**: Partner's IT team / system administrator.  
> **Prerequisite**: Access credentials provided by Brack/Alltron.

---

## 1. Connection Details

Obtain the following from Brack/Alltron before you begin:

| Parameter | Description | Example |
|-----------|-------------|---------|
| **Host** | sFTP server hostname or IP | `sftp.brack.ch` |
| **Port** | SSH port (default 22) | `22` |
| **Username** | Account assigned to your organisation | `partner_acme` |
| **Authentication** | SSH key (preferred) or password | See below |
| **Outbound directory** | Where you upload product/pricing/stock files | `/outbound` |
| **Inbound directory** | Where you download order files | `/inbound` |

> Fill these into `config/settings.yaml` under the `sftp:` section once confirmed.

---

## 2. Authentication Setup

### Option A — SSH Key Pair (Recommended)

SSH keys are more secure than passwords and don't require periodic rotation.

**Step 1: Generate a key pair** (if you don't have one)

```bash
ssh-keygen -t ed25519 -C "partner-integration" -f ./id_integration
```

This creates:
- `id_integration` — your **private key** (keep secret, never share)
- `id_integration.pub` — your **public key** (send to Brack/Alltron)

**Step 2: Send the public key to Brack/Alltron**

Email `id_integration.pub` to your Brack/Alltron technical contact. They will add it to the sFTP server's `authorized_keys`.

**Step 3: Configure the bridge**

In `config/settings.yaml`:
```yaml
sftp:
  host: sftp.brack.ch
  username: partner_acme
  private_key_path: ./id_integration    # path to your private key
  password: ""                           # leave empty when using key
```

### Option B — Password

In `.env` (never commit this file to git):
```
SFTP_PASSWORD=your_password_here
```

In `config/settings.yaml`:
```yaml
sftp:
  host: sftp.brack.ch
  username: partner_acme
  private_key_path: ""                   # leave empty when using password
```

---

## 3. Host Key Verification

The bridge **rejects unknown hosts** by default to prevent man-in-the-middle attacks. You must register the server's host key before the first connection.

**Step 1: Scan the server's fingerprint**

```bash
ssh-keyscan -p 22 sftp.brack.ch
```

You'll see output like:
```
sftp.brack.ch ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA...
sftp.brack.ch ssh-rsa AAAAB3NzaC1yc2EAAA...
```

**Step 2: Verify the fingerprint**

Contact Brack/Alltron to confirm the fingerprint matches their server. This is a one-time security check.

**Step 3: Add to known_hosts**

```bash
ssh-keyscan -p 22 sftp.brack.ch >> ~/.ssh/known_hosts
```

**Step 4: Test manually**

```bash
sftp -P 22 partner_acme@sftp.brack.ch
# If using key:
sftp -i ./id_integration -P 22 partner_acme@sftp.brack.ch
```

You should see the `sftp>` prompt. Type `ls /outbound` and `ls /inbound` to confirm the directories exist.

---

## 4. Firewall Rules

Ensure your network allows **outbound** connections to:

| Direction | Protocol | Destination | Port |
|-----------|----------|-------------|------|
| Outbound | TCP | `sftp.brack.ch` (resolve IP) | `22` |

If you're behind a corporate firewall or proxy, you may need to request an exception from your network team. Provide them:
- Destination hostname: `sftp.brack.ch`
- Port: 22
- Protocol: SSH/sFTP
- Purpose: Automated B2B data exchange

---

## 5. Directory Structure on the sFTP Server

After connecting, the server is expected to have:

```
/
├── outbound/       ← You upload files here (products, pricing, stock)
│   ├── PRODUCTS_20260330_143000.csv
│   ├── PRICING_20260330_143000.csv
│   └── STOCK_20260330_143000.csv
│
└── inbound/        ← Brack/Alltron places order files here
    ├── ORDERS_20260330_100000.csv
    └── ORDERS_20260330_120000.csv
```

- Files you upload to `/outbound` are picked up and processed by Brack/Alltron's systems
- Order files in `/inbound` are downloaded by the bridge, then deleted from the server after successful processing

---

## 6. Connectivity Test Checklist

Run through this before proceeding to integration testing:

| # | Test | Command / Action | Expected Result |
|---|------|-----------------|-----------------|
| 1 | DNS resolves | `nslookup sftp.brack.ch` | Returns an IP address |
| 2 | Port reachable | `nc -zv sftp.brack.ch 22` | "Connection ... succeeded" |
| 3 | SSH handshake | `ssh -v partner_acme@sftp.brack.ch` | Key exchange completes, auth prompt |
| 4 | Host key trusted | `ssh-keygen -F sftp.brack.ch` | Shows a matching key |
| 5 | sFTP login | `sftp partner_acme@sftp.brack.ch` | `sftp>` prompt |
| 6 | List outbound | `ls /outbound` (at sftp prompt) | Directory listing (possibly empty) |
| 7 | List inbound | `ls /inbound` (at sftp prompt) | Directory listing |
| 8 | Upload test file | `put test.txt /outbound/test.txt` | No error |
| 9 | Download test file | `get /outbound/test.txt` | File downloaded locally |
| 10 | Clean up | `rm /outbound/test.txt` | Test file removed |

Once all 10 pass, your connectivity is confirmed. Proceed to the Integration Test Plan.

---

## 7. Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `Connection timed out` | Firewall blocking port 22 | Request firewall exception (see §4) |
| `Host key verification failed` | Host key not in known_hosts | Run `ssh-keyscan` (see §3) |
| `Permission denied (publickey)` | Public key not registered on server | Send `.pub` file to Brack/Alltron |
| `Permission denied (password)` | Wrong password or account locked | Verify credentials with Brack/Alltron |
| `No such file or directory: /outbound` | Wrong remote directory path | Confirm paths with Brack/Alltron |
| `Network is unreachable` | No internet or VPN required | Check network/VPN connection |

---

## 8. Security Notes

- **Never share your private key**. Only the `.pub` file goes to Brack/Alltron.
- **Keep `.env` out of version control**. It's already in `.gitignore`.
- **Rotate credentials periodically**. Agree on a rotation schedule with Brack/Alltron (e.g. annually).
- **The bridge uses RejectPolicy** for host keys — it will refuse to connect to an unrecognised server. This is intentional security, not a bug.
