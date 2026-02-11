"""Tests for storage module."""

from datetime import datetime
from decimal import Decimal

import pytest

from bozo.storage import DatabaseNotInitializedError, TransactionStorage
from bozo.transaction import JournalEntry, LineItem


@pytest.fixture
def storage(tmp_path):
    """Create a storage instance with an initialized database."""
    return TransactionStorage.init_database(tmp_path / "test.bozo")


def make_entry(description="Test", debit_acct="cash", credit_acct="revenue", amount="50.00"):
    """Helper to create a journal entry."""
    return JournalEntry(
        description=description,
        timestamp=datetime(2024, 1, 15, 10, 30),
        line_items=[
            LineItem(account=debit_acct, debit=Decimal(amount)),
            LineItem(account=credit_acct, credit=Decimal(amount)),
        ],
    )


def test_add_entry(storage):
    """Test adding a journal entry."""
    entry_id = storage.add(make_entry())
    assert entry_id == 1


def test_get_all_entries(storage):
    """Test retrieving all journal entries."""
    storage.add(make_entry("Salary"))
    storage.add(make_entry("Groceries", "expenses", "cash", "25.00"))
    entries = storage.get_all()
    assert len(entries) == 2


def test_get_by_id(storage):
    """Test retrieving a journal entry by ID."""
    entry_id = storage.add(make_entry("Salary"))
    retrieved = storage.get_by_id(entry_id)
    assert retrieved is not None
    assert retrieved.description == "Salary"
    assert len(retrieved.line_items) == 2
    assert retrieved.line_items[0].debit == Decimal("50.00")
    assert retrieved.line_items[1].credit == Decimal("50.00")


def test_get_by_id_not_found(storage):
    """Test retrieving a non-existent entry."""
    assert storage.get_by_id(999) is None


def test_get_by_account(storage):
    """Test filtering entries by account."""
    storage.add(make_entry("Salary", "cash", "revenue", "1000.00"))
    storage.add(make_entry("Groceries", "expenses", "cash", "30.00"))
    storage.add(make_entry("Rent", "expenses", "cash", "500.00"))

    cash_entries = storage.get_by_account("cash")
    assert len(cash_entries) == 3  # cash appears in all three

    expenses_entries = storage.get_by_account("expenses")
    assert len(expenses_entries) == 2

    revenue_entries = storage.get_by_account("revenue")
    assert len(revenue_entries) == 1


def test_get_by_account_empty(storage):
    """Test filtering by non-existent account."""
    assert storage.get_by_account("nonexistent") == []


def test_immutable_no_delete_journal_entry(storage):
    """Test that journal entries cannot be deleted."""
    entry_id = storage.add(make_entry())
    with storage._get_connection() as conn:
        try:
            conn.execute("DELETE FROM journal_entries WHERE id = ?", (entry_id,))
            assert False, "Delete should have been prevented"
        except Exception as e:
            assert "cannot be deleted" in str(e)
    assert storage.get_by_id(entry_id) is not None


def test_immutable_no_update_journal_entry(storage):
    """Test that journal entries cannot be modified."""
    entry_id = storage.add(make_entry())
    with storage._get_connection() as conn:
        try:
            conn.execute(
                "UPDATE journal_entries SET description = ? WHERE id = ?",
                ("hacked", entry_id),
            )
            assert False, "Update should have been prevented"
        except Exception as e:
            assert "cannot be modified" in str(e)


def test_immutable_no_delete_line_item(storage):
    """Test that line items cannot be deleted."""
    storage.add(make_entry())
    with storage._get_connection() as conn:
        try:
            conn.execute("DELETE FROM line_items WHERE id = 1")
            assert False, "Delete should have been prevented"
        except Exception as e:
            assert "cannot be deleted" in str(e)


def test_immutable_no_update_line_item(storage):
    """Test that line items cannot be modified."""
    storage.add(make_entry())
    with storage._get_connection() as conn:
        try:
            conn.execute("UPDATE line_items SET debit = '999.99' WHERE id = 1")
            assert False, "Update should have been prevented"
        except Exception as e:
            assert "cannot be modified" in str(e)


def test_get_trial_balance(storage):
    """Test trial balance calculation."""
    storage.add(make_entry("Salary", "cash", "revenue", "1000.00"))
    storage.add(make_entry("Groceries", "expenses", "cash", "50.00"))
    storage.add(make_entry("Utilities", "expenses", "cash", "100.00"))

    balance = storage.get_trial_balance()

    assert balance["cash"]["debits"] == Decimal("1000")
    assert balance["cash"]["credits"] == Decimal("150")
    assert balance["cash"]["net"] == Decimal("850")

    assert balance["expenses"]["debits"] == Decimal("150")
    assert balance["expenses"]["credits"] == Decimal("0")
    assert balance["expenses"]["net"] == Decimal("150")

    assert balance["revenue"]["debits"] == Decimal("0")
    assert balance["revenue"]["credits"] == Decimal("1000")
    assert balance["revenue"]["net"] == Decimal("-1000")


def test_trial_balance_empty(storage):
    """Test trial balance with no entries."""
    assert storage.get_trial_balance() == {}


def test_trial_balance_debits_equal_credits(storage):
    """Test that total debits always equal total credits."""
    storage.add(make_entry("Salary", "cash", "revenue", "1000.00"))
    storage.add(make_entry("Groceries", "expenses", "cash", "50.00"))

    balance = storage.get_trial_balance()
    total_debits = sum(v["debits"] for v in balance.values())
    total_credits = sum(v["credits"] for v in balance.values())
    assert total_debits == total_credits


def test_database_not_initialized_error(tmp_path):
    """Test that accessing an uninitialized database raises an error."""
    db_path = tmp_path / "nonexistent.bozo"
    with pytest.raises(DatabaseNotInitializedError) as exc_info:
        TransactionStorage(db_path)
    assert "not found" in str(exc_info.value)
    assert str(db_path) in str(exc_info.value)


def test_init_database(tmp_path):
    """Test initializing a new database."""
    db_path = tmp_path / "ledger.bozo"
    storage = TransactionStorage.init_database(db_path)
    assert db_path.exists()
    storage.add(make_entry())
    assert len(storage.get_all()) == 1
