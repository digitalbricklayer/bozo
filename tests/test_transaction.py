"""Tests for transaction module."""

from datetime import datetime
from decimal import Decimal

from bozo.transaction import Transaction


def test_transaction_creation():
    """Test creating a transaction."""
    t = Transaction(
        amount=Decimal("100.50"),
        description="Groceries",
        category="food",
        timestamp=datetime(2024, 1, 15, 10, 30),
    )
    assert t.amount == Decimal("100.50")
    assert t.description == "Groceries"
    assert t.category == "food"


def test_transaction_amount_conversion():
    """Test that float amounts are converted to Decimal."""
    t = Transaction(
        amount=100.50,
        description="Test",
        category="test",
        timestamp=datetime.now(),
    )
    assert isinstance(t.amount, Decimal)
    assert t.amount == Decimal("100.5")


def test_transaction_to_dict():
    """Test converting transaction to dictionary."""
    t = Transaction(
        amount=Decimal("50.00"),
        description="Coffee",
        category="food",
        timestamp=datetime(2024, 1, 15, 10, 30),
    )
    d = t.to_dict()
    assert d["amount"] == "50.00"
    assert d["description"] == "Coffee"
    assert d["category"] == "food"


def test_transaction_from_dict():
    """Test creating transaction from dictionary."""
    data = {
        "amount": "75.25",
        "description": "Book",
        "category": "entertainment",
        "timestamp": "2024-01-15T10:30:00",
    }
    t = Transaction.from_dict(data)
    assert t.amount == Decimal("75.25")
    assert t.description == "Book"
