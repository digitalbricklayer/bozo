"""Tests for transaction module."""

from datetime import datetime
from decimal import Decimal

import pytest

from bozo.transaction import Account, JournalEntry, LineItem, parse_account_path


def test_line_item_debit():
    """Test creating a debit line item."""
    item = LineItem(account="assets:cash", debit=Decimal("100.00"))
    assert item.account == "assets:cash"
    assert item.debit == Decimal("100.00")
    assert item.credit is None


def test_line_item_credit():
    """Test creating a credit line item."""
    item = LineItem(account="income:revenue", credit=Decimal("100.00"))
    assert item.account == "income:revenue"
    assert item.debit is None
    assert item.credit == Decimal("100.00")


def test_journal_entry_creation():
    """Test creating a journal entry with line items."""
    entry = JournalEntry(
        description="Salary",
        timestamp=datetime(2024, 1, 15, 10, 30),
        line_items=[
            LineItem(account="assets:cash", debit=Decimal("1000.00")),
            LineItem(account="income:revenue", credit=Decimal("1000.00")),
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


def test_parse_account_path_simple():
    """Test parsing a single-segment account."""
    acct_type, segments = parse_account_path("assets")
    assert acct_type == "asset"
    assert segments == ["assets"]


def test_parse_account_path_nested():
    """Test parsing a multi-segment account."""
    acct_type, segments = parse_account_path("assets:bank:checking")
    assert acct_type == "asset"
    assert segments == ["assets", "bank", "checking"]


def test_parse_account_path_case_insensitive():
    """Test that account paths are lowercased."""
    acct_type, segments = parse_account_path("Assets:Bank")
    assert acct_type == "asset"
    assert segments == ["assets", "bank"]


def test_parse_account_path_all_types():
    """Test all valid root segments."""
    expected = {
        "assets": "asset",
        "liabilities": "liability",
        "income": "income",
        "expenses": "expense",
        "capital": "capital",
        "drawings": "drawings",
    }
    for root, acct_type in expected.items():
        result_type, _ = parse_account_path(root)
        assert result_type == acct_type


def test_parse_account_path_invalid_root():
    """Test that invalid root segments raise ValueError."""
    with pytest.raises(ValueError, match="Invalid account root"):
        parse_account_path("badroot:foo")


def test_parse_account_path_empty():
    """Test that empty account name raises ValueError."""
    with pytest.raises(ValueError, match="Invalid account name"):
        parse_account_path("")


def test_account_dataclass():
    """Test Account dataclass creation."""
    acct = Account(name="assets:bank", type="asset", parent_id=1, id=2)
    assert acct.name == "assets:bank"
    assert acct.type == "asset"
    assert acct.parent_id == 1
    assert acct.id == 2


def test_account_defaults():
    """Test Account dataclass defaults."""
    acct = Account(name="assets", type="asset")
    assert acct.parent_id is None
    assert acct.id is None
