"""Command line interface for bozo."""

import argparse
import os
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from bozo import __version__
from bozo.storage import DatabaseNotInitializedError, TransactionStorage
from bozo.transaction import JournalEntry, LineItem


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        prog="bozo",
        description="A double-entry accounting CLI tool",
    )
    parser.add_argument(
        "-v", "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Init database command
    init_parser = subparsers.add_parser("init", help="Initialize the database")
    init_parser.add_argument("--name", required=True, help="Name of the database file (e.g. ledger)")
    init_parser.add_argument("--folder", type=Path, default=Path("."), help="Folder where the database is created (default: current directory)")

    # Record journal entry command
    record_parser = subparsers.add_parser("record", help="Record a journal entry")
    record_parser.add_argument("amount", type=float, help="Transaction amount")
    record_parser.add_argument("description", help="Entry description")
    record_parser.add_argument("--debit", required=True, help="Account to debit")
    record_parser.add_argument("--credit", required=True, help="Account to credit")
    record_parser.add_argument(
        "-d", "--database",
        type=Path,
        default=None,
        help="Path to the database file (default: BOZO_DB env var)",
    )

    # List entries command
    list_parser = subparsers.add_parser("list", help="List journal entries")
    list_parser.add_argument(
        "-a", "--account",
        help="Filter by account",
    )
    list_parser.add_argument(
        "-d", "--database",
        type=Path,
        default=None,
        help="Path to the database file (default: BOZO_DB env var)",
    )

    # Summary command
    summary_parser = subparsers.add_parser("summary", help="Show trial balance")
    summary_parser.add_argument(
        "-d", "--database",
        type=Path,
        default=None,
        help="Path to the database file (default: BOZO_DB env var)",
    )

    return parser


def cmd_init(args) -> int:
    """Handle the init command."""
    folder = args.folder.resolve()
    db_path = folder / f"{args.name}.bozo"

    if db_path.exists():
        print(f"Database already exists at '{db_path}'.")
        return 1

    if not folder.is_dir():
        print(f"Error: Folder '{folder}' does not exist.", file=sys.stderr)
        return 1

    TransactionStorage.init_database(db_path)
    print(f"Initialized database at '{db_path}'.")
    return 0


def cmd_record(args, storage: TransactionStorage) -> int:
    """Handle the record command."""
    amount = Decimal(str(args.amount))
    entry = JournalEntry(
        description=args.description,
        timestamp=datetime.now(),
        line_items=[
            LineItem(account=args.debit, debit=amount),
            LineItem(account=args.credit, credit=amount),
        ],
    )
    entry_id = storage.add(entry)
    print(f"Recorded entry #{entry_id}: {amount:.2f} - {args.description} [debit: {args.debit}, credit: {args.credit}]")
    return 0


def cmd_list(args, storage: TransactionStorage) -> int:
    """Handle the list command."""
    if args.account:
        entries = storage.get_by_account(args.account)
    else:
        entries = storage.get_all()

    if not entries:
        print("No journal entries found.")
        return 0

    print(f"{'ID':<6} {'Date':<12} {'Description':<20} {'Debit Acct':<15} {'Credit Acct':<15} {'Amount':>10}")
    print("-" * 80)
    for entry in entries:
        debit_item = next((li for li in entry.line_items if li.debit is not None), None)
        credit_item = next((li for li in entry.line_items if li.credit is not None), None)
        amount = debit_item.debit if debit_item else Decimal("0")
        debit_acct = debit_item.account if debit_item else ""
        credit_acct = credit_item.account if credit_item else ""
        print(f"{entry.id:<6} {entry.timestamp.strftime('%Y-%m-%d'):<12} {entry.description:<20} {debit_acct:<15} {credit_acct:<15} {amount:>10.2f}")

    return 0


def cmd_summary(storage: TransactionStorage) -> int:
    """Handle the summary command."""
    accounts = storage.get_trial_balance()

    if not accounts:
        print("No journal entries recorded yet.")
        return 0

    print("=== Trial Balance ===\n")
    print(f"{'Account':<20} {'Debits':>12} {'Credits':>12} {'Net':>12}")
    print("-" * 58)

    total_debits = Decimal("0")
    total_credits = Decimal("0")
    for account, data in accounts.items():
        print(f"{account:<20} {data['debits']:>12.2f} {data['credits']:>12.2f} {data['net']:>12.2f}")
        total_debits += data["debits"]
        total_credits += data["credits"]

    print("-" * 58)
    print(f"{'TOTAL':<20} {total_debits:>12.2f} {total_credits:>12.2f} {total_debits - total_credits:>12.2f}")

    return 0


def main(argv: list[str] | None = None) -> int:
    """Main entry point for the CLI."""
    parser = create_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    if args.command == "init":
        return cmd_init(args)

    # Resolve database path from -d flag or BOZO_DB env var
    db_path = args.database
    if db_path is None:
        env_db = os.environ.get("BOZO_DB")
        if env_db:
            db_path = Path(env_db)
        else:
            print("Error: No database specified. Use -d or set BOZO_DB environment variable.", file=sys.stderr)
            return 1

    try:
        storage = TransactionStorage(db_path)
    except DatabaseNotInitializedError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    if args.command == "record":
        return cmd_record(args, storage)

    if args.command == "list":
        return cmd_list(args, storage)

    if args.command == "summary":
        return cmd_summary(storage)

    return 0


if __name__ == "__main__":
    sys.exit(main())
