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

### Set the default database

Instead of passing `-d` to every command, set the `BOZO_DB` environment variable:

```bash
export BOZO_DB=ledger.bozo
```

All commands below will use this database unless `-d` is specified.

### Record a transaction

```bash
bozo record 50.00 "Freelance payment" -c income
bozo record -25.50 "Groceries" -c food
```

Or specify the database explicitly:

```bash
bozo record 50.00 "Freelance payment" -c income -d ledger.bozo
```

### List transactions

```bash
bozo list
bozo list -c food
```

### View summary

```bash
bozo summary
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
