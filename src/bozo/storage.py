"""SQLite storage for transactions."""

import sqlite3
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from bozo.transaction import Transaction

class DatabaseNotInitializedError(Exception):
    """Raised when trying to use a database that hasn't been initialized."""
    pass


class TransactionStorage:
    """SQLite-based storage for transactions."""

    def __init__(self, db_path: Path, require_init: bool = True):
        """Initialize storage with a database file path.

        Args:
            db_path: Full path to the SQLite database file.
            require_init: If True, raise error if database doesn't exist.
        """
        self.db_path = Path(db_path)

        if require_init and not self.db_path.exists():
            raise DatabaseNotInitializedError(
                f"Database not found at '{self.db_path}'. "
                f"Run 'bozo init --name <name> --folder <folder>' first."
            )

    @classmethod
    def init_database(cls, db_path: Path) -> "TransactionStorage":
        """Initialize a new database at the given path.

        Args:
            db_path: Full path to the SQLite database file.

        Returns:
            TransactionStorage instance for the new database.
        """
        db_path = Path(db_path)
        storage = cls(db_path, require_init=False)
        storage._init_db()
        return storage

    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection."""
        return sqlite3.connect(self.db_path)

    def _init_db(self) -> None:
        """Initialize the database schema with immutable ledger constraints."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    amount TEXT NOT NULL,
                    description TEXT NOT NULL,
                    category TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
            """)
            # Prevent updates to transactions (immutable ledger)
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS prevent_transaction_update
                BEFORE UPDATE ON transactions
                BEGIN
                    SELECT RAISE(ABORT, 'Transactions cannot be modified');
                END
            """)
            # Prevent deletes from transactions (immutable ledger)
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS prevent_transaction_delete
                BEFORE DELETE ON transactions
                BEGIN
                    SELECT RAISE(ABORT, 'Transactions cannot be deleted');
                END
            """)
            conn.commit()

    def add(self, transaction: Transaction) -> int:
        """Add a transaction and return its ID."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO transactions (amount, description, category, timestamp)
                VALUES (?, ?, ?, ?)
                """,
                (
                    str(transaction.amount),
                    transaction.description,
                    transaction.category,
                    transaction.timestamp.isoformat(),
                ),
            )
            conn.commit()
            return cursor.lastrowid

    def get_all(self) -> list[Transaction]:
        """Get all transactions."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM transactions ORDER BY timestamp DESC"
            )
            return [self._row_to_transaction(row) for row in cursor.fetchall()]

    def get_by_id(self, transaction_id: int) -> Transaction | None:
        """Get a transaction by ID."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM transactions WHERE id = ?",
                (transaction_id,),
            )
            row = cursor.fetchone()
            return self._row_to_transaction(row) if row else None

    def get_by_category(self, category: str) -> list[Transaction]:
        """Get all transactions in a category."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM transactions WHERE category = ? ORDER BY timestamp DESC",
                (category,),
            )
            return [self._row_to_transaction(row) for row in cursor.fetchall()]

    def get_summary(self) -> dict:
        """Get a summary of all transactions."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row

            # Total income and expenses
            cursor = conn.execute("""
                SELECT
                    SUM(CASE WHEN CAST(amount AS REAL) > 0 THEN CAST(amount AS REAL) ELSE 0 END) as income,
                    SUM(CASE WHEN CAST(amount AS REAL) < 0 THEN CAST(amount AS REAL) ELSE 0 END) as expenses,
                    COUNT(*) as count
                FROM transactions
            """)
            row = cursor.fetchone()

            # By category
            cursor = conn.execute("""
                SELECT category, SUM(CAST(amount AS REAL)) as total, COUNT(*) as count
                FROM transactions
                GROUP BY category
                ORDER BY total DESC
            """)
            categories = {
                r["category"]: {"total": Decimal(str(r["total"] or 0)), "count": r["count"]}
                for r in cursor.fetchall()
            }

            return {
                "income": Decimal(str(row["income"] or 0)),
                "expenses": Decimal(str(row["expenses"] or 0)),
                "balance": Decimal(str((row["income"] or 0) + (row["expenses"] or 0))),
                "count": row["count"],
                "by_category": categories,
            }

    def _row_to_transaction(self, row: sqlite3.Row) -> Transaction:
        """Convert a database row to a Transaction."""
        return Transaction(
            id=row["id"],
            amount=Decimal(row["amount"]),
            description=row["description"],
            category=row["category"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
        )
