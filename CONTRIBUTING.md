# Contributing to B2B Data Bridge

Thank you for considering contributing! This guide will help you get started.

## Development Setup

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/b2b-data-bridge.git
cd b2b-data-bridge

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate

# Install with dev dependencies
pip install -e ".[dev]"

# Verify everything works
pytest
```

## Making Changes

1. **Fork** the repository and create a feature branch from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Write code** following the existing patterns:
   - Keep modules focused — one responsibility per file
   - Use type hints
   - Validate at system boundaries (incoming files, user input)
   - Don't over-engineer — match the existing simplicity

3. **Write tests** for your changes:
   ```bash
   pytest                          # run all tests
   pytest tests/test_your_file.py  # run specific tests
   pytest --cov=b2b_data_bridge    # check coverage
   ```

4. **Lint** your code:
   ```bash
   ruff check src/ tests/
   ruff format src/ tests/
   ```

5. **Commit** with clear, conventional messages:
   ```
   feat: add XLSX support for outbound pricing files
   fix: handle empty EAN field in order parsing
   docs: update sFTP setup guide with Windows instructions
   test: add edge case for multi-line orders
   ```

6. **Push** and open a Pull Request against `main`.

## Commit Convention

We use [Conventional Commits](https://www.conventionalcommits.org/):

| Prefix | Use for |
|--------|---------|
| `feat:` | New features or capabilities |
| `fix:` | Bug fixes |
| `docs:` | Documentation changes only |
| `test:` | Adding or updating tests |
| `refactor:` | Code changes that don't add features or fix bugs |
| `chore:` | Build, CI, dependency updates |

## Code Style

- **Python 3.9+** — no walrus operators or other 3.10+ features
- **Line length**: 100 characters (configured in `pyproject.toml`)
- **Formatter**: ruff
- **Type hints**: yes, for function signatures
- **Docstrings**: for modules and public functions; skip for obvious helpers

## Project Structure

```
src/b2b_data_bridge/
├── config.py       # Settings loading (YAML + .env)
├── models.py       # Pydantic models + mapping functions
├── validation.py   # Field validation, EAN checks
├── files.py        # CSV/XLSX I/O, archiving
├── sftp.py         # sFTP transport + local fallback
├── export.py       # Outbound pipeline
├── orders.py       # Inbound pipeline
└── main.py         # CLI entry point
```

Keep it flat — no nested packages unless there's a strong reason.

## What We're Looking For

- Bug fixes with a test case that reproduces the issue
- New file format support (e.g., XML, JSON)
- Additional distributor integrations
- Better error messages and logging
- Windows-specific improvements
- Documentation improvements

## What We're NOT Looking For

- Framework overhead (no Flask, FastAPI, Celery — this is a CLI tool)
- Database ORMs (keep the store interface simple)
- Breaking changes to the CSV format without distributor agreement

## Questions?

Open an issue for discussion before starting major work. This helps avoid duplicate effort and ensures alignment with the project direction.
