# Bozo

A command line tool for recording immutable financial transactions.

## Installation

```bash
pip install -e ".[dev]"
```

## Usage

### Initialize a database

```bash
bozo init --name ledger --folder .
```

This creates `ledger.db` in the current directory.

### Record a transaction

```bash
bozo record 50.00 "Freelance payment" -c income -d ledger.db
bozo record -25.50 "Groceries" -c food -d ledger.db
```

### List transactions

```bash
bozo list -d ledger.db
bozo list -c food -d ledger.db
```

### View summary

```bash
bozo summary -d ledger.db
```

## Design

- Transactions are **immutable** — once recorded, they cannot be modified or deleted (enforced by SQLite triggers)
- Amounts are stored with decimal precision
- Each database is a standalone `.db` file

## Development

```bash
pip install -e ".[dev]"
python -m pytest tests/ -v
```

## License

MIT
