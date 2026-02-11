# CLAUDE.md

## Project overview
Bozo is a CLI tool for recording immutable financial transactions, stored in SQLite.

## Tech stack
- Python 3.9+
- SQLite3 (stdlib)
- argparse for CLI
- pytest for testing

## Project structure
- `src/bozo/` - source code
  - `cli.py` - CLI entry point and command handlers
  - `storage.py` - SQLite storage layer (immutable ledger with triggers)
  - `transaction.py` - Transaction data model
- `tests/` - pytest tests

## Build & test commands
- Install in dev mode: `pip install -e ".[dev]"`
- Run all tests: `python -m pytest tests/ -v`
- Run a single test file: `python -m pytest tests/test_storage.py -v`

## Key conventions
- Transactions are immutable (enforced by SQLite triggers - no updates or deletes)
- Amounts stored as Decimal (via TEXT in SQLite) for precision
- Database is a standalone `.bozo` file; no directory creation on init
- CLI uses `--name` and `--folder` for init, `--database`/`-d` for other commands
