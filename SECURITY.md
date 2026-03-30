# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.0.x   | Yes       |

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly:

1. **Do NOT open a public GitHub issue** for security vulnerabilities
2. Email the maintainer directly (see profile) with:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
3. You will receive an acknowledgement within 48 hours
4. A fix will be developed and released as soon as possible

## Security Design

This project follows these security principles:

- **SSH host key verification**: Uses `RejectPolicy` — refuses connections to unknown servers (prevents man-in-the-middle attacks)
- **Credential handling**: Passwords stored in `.env` (gitignored), masked in `__repr__` and logs
- **Path traversal protection**: Downloads validate filenames and enforce directory containment
- **Input validation**: All incoming CSV/XLSX data is validated before processing
- **Row limits**: Parsers cap at 500,000 rows to prevent memory exhaustion
- **No code execution**: Files are parsed as data only — no `eval()`, no macros
- **Dependency minimalism**: Only 5 runtime dependencies, all well-maintained

## Dependencies

| Package | Purpose | Security notes |
|---------|---------|---------------|
| paramiko | sFTP/SSH | Widely audited SSH implementation |
| pydantic | Data validation | Input sanitisation via schema validation |
| openpyxl | XLSX read/write | Read-only mode used for parsing |
| pyyaml | Config loading | `safe_load()` only — no arbitrary object creation |
| python-dotenv | Env var loading | Reads `.env` files, no network access |
