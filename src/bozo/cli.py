"""Command line interface for bozo."""

import argparse
import sys
from datetime import datetime
from pathlib import Path

from bozo import __version__
from bozo.storage import DatabaseNotInitializedError, TransactionStorage
from bozo.transaction import Transaction


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        prog="bozo",
        description="A command line tool for recording financial transactions",
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

    # Record transaction command
    record_parser = subparsers.add_parser("record", help="Record a new transaction")
    record_parser.add_argument("amount", type=float, help="Transaction amount (positive=income, negative=expense)")
    record_parser.add_argument("description", help="Transaction description")
    record_parser.add_argument(
        "-c", "--category",
        default="uncategorized",
        help="Transaction category",
    )
    record_parser.add_argument(
        "-d", "--database",
        type=Path,
        required=True,
        help="Path to the database file",
    )

    # List transactions command
    list_parser = subparsers.add_parser("list", help="List all transactions")
    list_parser.add_argument(
        "-c", "--category",
        help="Filter by category",
    )
    list_parser.add_argument(
        "-d", "--database",
        type=Path,
        required=True,
        help="Path to the database file",
    )

    # Summary command
    summary_parser = subparsers.add_parser("summary", help="Show transaction summary")
    summary_parser.add_argument(
        "-d", "--database",
        type=Path,
        required=True,
        help="Path to the database file",
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
    transaction = Transaction(
        amount=args.amount,
        description=args.description,
        category=args.category,
        timestamp=datetime.now(),
    )
    tx_id = storage.add(transaction)
    sign = "+" if args.amount >= 0 else ""
    print(f"Recorded transaction #{tx_id}: {sign}{args.amount:.2f} - {args.description} [{args.category}]")
    return 0


def cmd_list(args, storage: TransactionStorage) -> int:
    """Handle the list command."""
    if args.category:
        transactions = storage.get_by_category(args.category)
    else:
        transactions = storage.get_all()

    if not transactions:
        print("No transactions found.")
        return 0

    print(f"{'ID':<6} {'Date':<12} {'Amount':>12} {'Category':<15} Description")
    print("-" * 70)
    for tx in transactions:
        sign = "+" if tx.amount >= 0 else ""
        print(f"{tx.id:<6} {tx.timestamp.strftime('%Y-%m-%d'):<12} {sign}{tx.amount:>11.2f} {tx.category:<15} {tx.description}")

    return 0


def cmd_summary(storage: TransactionStorage) -> int:
    """Handle the summary command."""
    summary = storage.get_summary()

    if summary["count"] == 0:
        print("No transactions recorded yet.")
        return 0

    print("=== Transaction Summary ===\n")
    print(f"Total transactions: {summary['count']}")
    print(f"Income:   +{summary['income']:>10.2f}")
    print(f"Expenses:  {summary['expenses']:>10.2f}")
    print(f"Balance:   {summary['balance']:>10.2f}")

    if summary["by_category"]:
        print("\n--- By Category ---")
        for category, data in summary["by_category"].items():
            sign = "+" if data["total"] >= 0 else ""
            print(f"  {category:<15} {sign}{data['total']:>10.2f}  ({data['count']} transactions)")

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

    # Commands that require an initialized database
    try:
        storage = TransactionStorage(args.database)
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
