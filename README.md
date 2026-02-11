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

This creates `ledger.bozo` in the current directory.

### Record a transaction

```bash
bozo record 50.00 "Freelance payment" -c income -d ledger.bozo
bozo record -25.50 "Groceries" -c food -d ledger.bozo
```

### List transactions

```bash
bozo list -d ledger.bozo
bozo list -c food -d ledger.bozo
```

### View summary

```bash
bozo summary -d ledger.bozo
```

## Design

- Transactions are **immutable** — once recorded, they cannot be modified or deleted (enforced by SQLite triggers)
- Amounts are stored with decimal precision
- Each database is a standalone `.bozo` file

## Development

```bash
pip install -e ".[dev]"
python -m pytest tests/ -v
```

## License

MIT
