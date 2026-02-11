"""SQLite storage for double-entry journal entries."""

import sqlite3
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from bozo.transaction import Account, JournalEntry, LineItem, parse_account_path


class DatabaseNotInitializedError(Exception):
    """Raised when trying to use a database that hasn't been initialized."""
    pass


class TransactionStorage:
    """SQLite-based storage for journal entries."""

    def __init__(self, db_path: Path, require_init: bool = True):
        self.db_path = Path(db_path)
        if require_init and not self.db_path.exists():
            raise DatabaseNotInitializedError(
                f"Database not found at '{self.db_path}'. "
                f"Run 'bozo init --name <name> --folder <folder>' first."
            )

    @classmethod
    def init_database(cls, db_path: Path) -> "TransactionStorage":
        db_path = Path(db_path)
        storage = cls(db_path, require_init=False)
        storage._init_db()
        return storage

    def _get_connection(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS journal_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    description TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS line_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    journal_entry_id INTEGER NOT NULL REFERENCES journal_entries(id),
                    account TEXT NOT NULL,
                    debit TEXT,
                    credit TEXT,
                    CHECK (
                        (debit IS NOT NULL AND credit IS NULL) OR
                        (debit IS NULL AND credit IS NOT NULL)
                    )
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    type TEXT NOT NULL CHECK (type IN ('asset','liability','income','expense','capital','drawings')),
                    parent_id INTEGER REFERENCES accounts(id)
                )
            """)
            # Immutability triggers for journal_entries
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS prevent_journal_entry_update
                BEFORE UPDATE ON journal_entries
                BEGIN
                    SELECT RAISE(ABORT, 'Journal entries cannot be modified');
                END
            """)
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS prevent_journal_entry_delete
                BEFORE DELETE ON journal_entries
                BEGIN
                    SELECT RAISE(ABORT, 'Journal entries cannot be deleted');
                END
            """)
            # Immutability triggers for line_items
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS prevent_line_item_update
                BEFORE UPDATE ON line_items
                BEGIN
                    SELECT RAISE(ABORT, 'Line items cannot be modified');
                END
            """)
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS prevent_line_item_delete
                BEFORE DELETE ON line_items
                BEGIN
                    SELECT RAISE(ABORT, 'Line items cannot be deleted');
                END
            """)
            conn.commit()

    def _ensure_account(self, conn: sqlite3.Connection, account_name: str) -> None:
        """Validate and auto-create the account and its ancestor chain."""
        account_name = account_name.lower()
        acct_type, segments = parse_account_path(account_name)
        for i in range(1, len(segments) + 1):
            path = ":".join(segments[:i])
            existing = conn.execute(
                "SELECT id FROM accounts WHERE name = ?", (path,)
            ).fetchone()
            if existing:
                continue
            parent_id = None
            if i > 1:
                parent_path = ":".join(segments[: i - 1])
                parent_row = conn.execute(
                    "SELECT id FROM accounts WHERE name = ?", (parent_path,)
                ).fetchone()
                if parent_row:
                    parent_id = parent_row[0]
            conn.execute(
                "INSERT INTO accounts (name, type, parent_id) VALUES (?, ?, ?)",
                (path, acct_type, parent_id),
            )

    def add(self, entry: JournalEntry) -> int:
        with self._get_connection() as conn:
            for item in entry.line_items:
                self._ensure_account(conn, item.account)
            cursor = conn.execute(
                "INSERT INTO journal_entries (description, timestamp) VALUES (?, ?)",
                (entry.description, entry.timestamp.isoformat()),
            )
            entry_id = cursor.lastrowid
            for item in entry.line_items:
                conn.execute(
                    "INSERT INTO line_items (journal_entry_id, account, debit, credit) VALUES (?, ?, ?, ?)",
                    (
                        entry_id,
                        item.account.lower(),
                        str(item.debit) if item.debit is not None else None,
                        str(item.credit) if item.credit is not None else None,
                    ),
                )
            conn.commit()
            return entry_id

    def get_all(self) -> list[JournalEntry]:
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            entries = conn.execute(
                "SELECT * FROM journal_entries ORDER BY timestamp DESC"
            ).fetchall()
            return [self._load_entry(conn, row) for row in entries]

    def get_by_id(self, entry_id: int) -> JournalEntry | None:
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM journal_entries WHERE id = ?", (entry_id,)
            ).fetchone()
            if row is None:
                return None
            return self._load_entry(conn, row)

    def get_by_account(self, account: str) -> list[JournalEntry]:
        account = account.lower()
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            entry_ids = conn.execute(
                "SELECT DISTINCT journal_entry_id FROM line_items WHERE account = ? OR account LIKE ?",
                (account, account + ":%"),
            ).fetchall()
            ids = [r["journal_entry_id"] for r in entry_ids]
            if not ids:
                return []
            placeholders = ",".join("?" * len(ids))
            entries = conn.execute(
                f"SELECT * FROM journal_entries WHERE id IN ({placeholders}) ORDER BY timestamp DESC",
                ids,
            ).fetchall()
            return [self._load_entry(conn, row) for row in entries]

    def get_accounts(self, account_type: str | None = None) -> list[Account]:
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            if account_type:
                rows = conn.execute(
                    "SELECT * FROM accounts WHERE type = ? ORDER BY name",
                    (account_type,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM accounts ORDER BY name"
                ).fetchall()
            return [
                Account(
                    id=row["id"],
                    name=row["name"],
                    type=row["type"],
                    parent_id=row["parent_id"],
                )
                for row in rows
            ]

    def get_trial_balance(self, account: str | None = None) -> dict:
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            if account:
                account = account.lower()
                rows = conn.execute("""
                    SELECT
                        account,
                        SUM(CASE WHEN debit IS NOT NULL THEN CAST(debit AS REAL) ELSE 0 END) as total_debits,
                        SUM(CASE WHEN credit IS NOT NULL THEN CAST(credit AS REAL) ELSE 0 END) as total_credits
                    FROM line_items
                    WHERE account = ? OR account LIKE ?
                    GROUP BY account
                    ORDER BY account
                """, (account, account + ":%")).fetchall()
            else:
                rows = conn.execute("""
                    SELECT
                        account,
                        SUM(CASE WHEN debit IS NOT NULL THEN CAST(debit AS REAL) ELSE 0 END) as total_debits,
                        SUM(CASE WHEN credit IS NOT NULL THEN CAST(credit AS REAL) ELSE 0 END) as total_credits
                    FROM line_items
                    GROUP BY account
                    ORDER BY account
                """).fetchall()
            accounts = {}
            for row in rows:
                total_debits = Decimal(str(row["total_debits"]))
                total_credits = Decimal(str(row["total_credits"]))
                accounts[row["account"]] = {
                    "debits": total_debits,
                    "credits": total_credits,
                    "net": total_debits - total_credits,
                }
            return accounts

    def _load_entry(self, conn: sqlite3.Connection, row: sqlite3.Row) -> JournalEntry:
        items = conn.execute(
            "SELECT * FROM line_items WHERE journal_entry_id = ?", (row["id"],)
        ).fetchall()
        line_items = [
            LineItem(
                id=item["id"],
                account=item["account"],
                debit=Decimal(item["debit"]) if item["debit"] is not None else None,
                credit=Decimal(item["credit"]) if item["credit"] is not None else None,
            )
            for item in items
        ]
        return JournalEntry(
            id=row["id"],
            description=row["description"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            line_items=line_items,
        )
