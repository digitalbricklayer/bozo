"""Tests for storage module."""

from datetime import datetime
from decimal import Decimal

import pytest

from bozo.storage import DatabaseNotInitializedError, TransactionStorage
from bozo.transaction import Transaction


@pytest.fixture
def storage(tmp_path):
    """Create a storage instance with an initialized database."""
    return TransactionStorage.init_database(tmp_path / "test.bozo")


@pytest.fixture
def sample_transaction():
    """Create a sample transaction."""
    return Transaction(
        amount=Decimal("50.00"),
        description="Test purchase",
        category="test",
        timestamp=datetime(2024, 1, 15, 10, 30),
    )


def test_add_transaction(storage, sample_transaction):
    """Test adding a transaction."""
    tx_id = storage.add(sample_transaction)
    assert tx_id == 1


def test_get_all_transactions(storage, sample_transaction):
    """Test retrieving all transactions."""
    storage.add(sample_transaction)
    storage.add(Transaction(
        amount=Decimal("-25.00"),
        description="Another purchase",
        category="food",
        timestamp=datetime(2024, 1, 16, 12, 0),
    ))

    transactions = storage.get_all()
    assert len(transactions) == 2


def test_get_by_id(storage, sample_transaction):
    """Test retrieving a transaction by ID."""
    tx_id = storage.add(sample_transaction)
    retrieved = storage.get_by_id(tx_id)

    assert retrieved is not None
    assert retrieved.amount == sample_transaction.amount
    assert retrieved.description == sample_transaction.description


def test_get_by_id_not_found(storage):
    """Test retrieving a non-existent transaction."""
    retrieved = storage.get_by_id(999)
    assert retrieved is None


def test_get_by_category(storage):
    """Test filtering transactions by category."""
    storage.add(Transaction(
        amount=Decimal("100.00"),
        description="Salary",
        category="income",
        timestamp=datetime(2024, 1, 1),
    ))
    storage.add(Transaction(
        amount=Decimal("-30.00"),
        description="Groceries",
        category="food",
        timestamp=datetime(2024, 1, 2),
    ))
    storage.add(Transaction(
        amount=Decimal("-15.00"),
        description="Lunch",
        category="food",
        timestamp=datetime(2024, 1, 3),
    ))

    food_transactions = storage.get_by_category("food")
    assert len(food_transactions) == 2
    assert all(tx.category == "food" for tx in food_transactions)


def test_transaction_immutable_no_delete(storage, sample_transaction):
    """Test that transactions cannot be deleted (immutable ledger)."""
    tx_id = storage.add(sample_transaction)
    with storage._get_connection() as conn:
        try:
            conn.execute("DELETE FROM transactions WHERE id = ?", (tx_id,))
            assert False, "Delete should have been prevented"
        except Exception as e:
            assert "cannot be deleted" in str(e)
    # Verify transaction still exists
    assert storage.get_by_id(tx_id) is not None


def test_transaction_immutable_no_update(storage, sample_transaction):
    """Test that transactions cannot be modified (immutable ledger)."""
    tx_id = storage.add(sample_transaction)
    with storage._get_connection() as conn:
        try:
            conn.execute(
                "UPDATE transactions SET amount = ? WHERE id = ?",
                ("999.99", tx_id),
            )
            assert False, "Update should have been prevented"
        except Exception as e:
            assert "cannot be modified" in str(e)
    # Verify transaction unchanged
    tx = storage.get_by_id(tx_id)
    assert tx.amount == sample_transaction.amount


def test_get_summary(storage):
    """Test getting transaction summary."""
    storage.add(Transaction(
        amount=Decimal("1000.00"),
        description="Salary",
        category="income",
        timestamp=datetime(2024, 1, 1),
    ))
    storage.add(Transaction(
        amount=Decimal("-50.00"),
        description="Groceries",
        category="food",
        timestamp=datetime(2024, 1, 2),
    ))
    storage.add(Transaction(
        amount=Decimal("-100.00"),
        description="Utilities",
        category="bills",
        timestamp=datetime(2024, 1, 3),
    ))

    summary = storage.get_summary()

    assert summary["income"] == Decimal("1000")
    assert summary["expenses"] == Decimal("-150")
    assert summary["balance"] == Decimal("850")
    assert summary["count"] == 3
    assert "income" in summary["by_category"]
    assert "food" in summary["by_category"]
    assert "bills" in summary["by_category"]


def test_empty_summary(storage):
    """Test summary with no transactions."""
    summary = storage.get_summary()
    assert summary["count"] == 0
    assert summary["income"] == Decimal("0")
    assert summary["expenses"] == Decimal("0")
    assert summary["balance"] == Decimal("0")


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
    # Should be able to use it immediately
    storage.add(Transaction(
        amount=Decimal("100.00"),
        description="Test",
        category="test",
        timestamp=datetime(2024, 1, 1),
    ))
    assert len(storage.get_all()) == 1
