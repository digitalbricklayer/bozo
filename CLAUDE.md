# CLAUDE.md

## Project overview
Bozo is a double-entry accounting CLI tool, stored in SQLite. Every journal entry has balanced debits and credits across ledger accounts.

## Tech stack
- Python 3.9+
- SQLite3 (stdlib)
- argparse for CLI
- pytest for testing

## Project structure
- `src/bozo/` - source code
  - `cli.py` - CLI entry point and command handlers
  - `storage.py` - SQLite storage layer (immutable ledger with triggers)
  - `transaction.py` - JournalEntry and LineItem data models
- `tests/` - pytest tests

## Build & test commands
- Install in dev mode: `pip install -e ".[dev]"`
- Run all tests: `python -m pytest tests/ -v`
- Run a single test file: `python -m pytest tests/test_storage.py -v`

## Key conventions
- Double-entry: every journal entry has debit and credit line items that must balance
- Journal entries and line items are immutable (enforced by SQLite triggers)
- Amounts stored as Decimal (via TEXT in SQLite) for precision
- Accounts are created on-the-fly when first used in a journal entry
- Database is a standalone `.bozo` file; no directory creation on init
- CLI uses `--name` and `--folder` for init, `--database`/`-d` for other commands
- Record syntax: `bozo record <amount> "<description>" --debit <account> --credit <account>`
