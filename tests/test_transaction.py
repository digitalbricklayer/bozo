"""Tests for transaction module."""

from datetime import datetime
from decimal import Decimal

from bozo.transaction import JournalEntry, LineItem


def test_line_item_debit():
    """Test creating a debit line item."""
    item = LineItem(account="cash", debit=Decimal("100.00"))
    assert item.account == "cash"
    assert item.debit == Decimal("100.00")
    assert item.credit is None


def test_line_item_credit():
    """Test creating a credit line item."""
    item = LineItem(account="revenue", credit=Decimal("100.00"))
    assert item.account == "revenue"
    assert item.debit is None
    assert item.credit == Decimal("100.00")


def test_journal_entry_creation():
    """Test creating a journal entry with line items."""
    entry = JournalEntry(
        description="Salary",
        timestamp=datetime(2024, 1, 15, 10, 30),
        line_items=[
            LineItem(account="cash", debit=Decimal("1000.00")),
            LineItem(account="revenue", credit=Decimal("1000.00")),
        ],
    )
    assert entry.description == "Salary"
    assert len(entry.line_items) == 2
    assert entry.line_items[0].debit == Decimal("1000.00")
    assert entry.line_items[1].credit == Decimal("1000.00")


def test_journal_entry_default_line_items():
    """Test that line_items defaults to empty list."""
    entry = JournalEntry(
        description="Empty",
        timestamp=datetime(2024, 1, 1),
    )
    assert entry.line_items == []
