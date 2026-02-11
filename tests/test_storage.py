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


def make_entry(description="Test", debit_acct="assets:cash", credit_acct="income:revenue", amount="50.00"):
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
    storage.add(make_entry("Groceries", "expenses:food", "assets:cash", "25.00"))
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
    storage.add(make_entry("Salary", "assets:cash", "income:revenue", "1000.00"))
    storage.add(make_entry("Groceries", "expenses:food", "assets:cash", "30.00"))
    storage.add(make_entry("Rent", "expenses:rent", "assets:cash", "500.00"))

    cash_entries = storage.get_by_account("assets:cash")
    assert len(cash_entries) == 3  # cash appears in all three

    expenses_entries = storage.get_by_account("expenses:food")
    assert len(expenses_entries) == 1

    revenue_entries = storage.get_by_account("income:revenue")
    assert len(revenue_entries) == 1


def test_get_by_account_prefix(storage):
    """Test that get_by_account matches subtrees."""
    storage.add(make_entry("Salary", "assets:bank:checking", "income:revenue", "1000.00"))
    storage.add(make_entry("Groceries", "expenses:food", "assets:bank:checking", "30.00"))
    storage.add(make_entry("Petty cash", "assets:cash", "assets:bank:checking", "50.00"))

    # "assets" should match all entries (all touch an assets: account)
    assets_entries = storage.get_by_account("assets")
    assert len(assets_entries) == 3

    # "assets:bank" should match entries that use assets:bank:checking
    bank_entries = storage.get_by_account("assets:bank")
    assert len(bank_entries) == 3

    # "assets:cash" matches only the petty cash entry (exact match)
    cash_entries = storage.get_by_account("assets:cash")
    assert len(cash_entries) == 1


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
    storage.add(make_entry("Salary", "assets:cash", "income:revenue", "1000.00"))
    storage.add(make_entry("Groceries", "expenses:food", "assets:cash", "50.00"))
    storage.add(make_entry("Utilities", "expenses:utilities", "assets:cash", "100.00"))

    balance = storage.get_trial_balance()

    assert balance["assets:cash"]["debits"] == Decimal("1000")
    assert balance["assets:cash"]["credits"] == Decimal("150")
    assert balance["assets:cash"]["net"] == Decimal("850")

    assert balance["expenses:food"]["debits"] == Decimal("50")
    assert balance["expenses:food"]["credits"] == Decimal("0")
    assert balance["expenses:food"]["net"] == Decimal("50")

    assert balance["expenses:utilities"]["debits"] == Decimal("100")
    assert balance["expenses:utilities"]["credits"] == Decimal("0")
    assert balance["expenses:utilities"]["net"] == Decimal("100")

    assert balance["income:revenue"]["debits"] == Decimal("0")
    assert balance["income:revenue"]["credits"] == Decimal("1000")
    assert balance["income:revenue"]["net"] == Decimal("-1000")


def test_trial_balance_scoped(storage):
    """Test trial balance scoped to an account subtree."""
    storage.add(make_entry("Salary", "assets:cash", "income:revenue", "1000.00"))
    storage.add(make_entry("Groceries", "expenses:food", "assets:cash", "50.00"))

    balance = storage.get_trial_balance(account="expenses")
    assert "expenses:food" in balance
    assert "assets:cash" not in balance
    assert "income:revenue" not in balance


def test_trial_balance_empty(storage):
    """Test trial balance with no entries."""
    assert storage.get_trial_balance() == {}


def test_trial_balance_debits_equal_credits(storage):
    """Test that total debits always equal total credits."""
    storage.add(make_entry("Salary", "assets:cash", "income:revenue", "1000.00"))
    storage.add(make_entry("Groceries", "expenses:food", "assets:cash", "50.00"))

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


def test_account_auto_creation(storage):
    """Test that accounts are auto-created in the accounts table."""
    storage.add(make_entry("Test", "assets:bank:checking", "income:salary", "100.00"))
    accounts = storage.get_accounts()
    names = [a.name for a in accounts]
    assert "assets" in names
    assert "assets:bank" in names
    assert "assets:bank:checking" in names
    assert "income" in names
    assert "income:salary" in names


def test_account_hierarchy_parent_ids(storage):
    """Test that parent_id is set correctly in account hierarchy."""
    storage.add(make_entry("Test", "assets:bank:checking", "income:revenue", "100.00"))
    accounts = storage.get_accounts()
    by_name = {a.name: a for a in accounts}

    assert by_name["assets"].parent_id is None
    assert by_name["assets:bank"].parent_id == by_name["assets"].id
    assert by_name["assets:bank:checking"].parent_id == by_name["assets:bank"].id


def test_account_types(storage):
    """Test that account types are inferred from root segment."""
    storage.add(make_entry("Test", "assets:cash", "liabilities:loan", "100.00"))
    accounts = storage.get_accounts()
    by_name = {a.name: a for a in accounts}

    assert by_name["assets"].type == "asset"
    assert by_name["assets:cash"].type == "asset"
    assert by_name["liabilities"].type == "liability"
    assert by_name["liabilities:loan"].type == "liability"


def test_get_accounts_filtered_by_type(storage):
    """Test filtering accounts by type."""
    storage.add(make_entry("Test", "assets:cash", "income:revenue", "100.00"))
    asset_accounts = storage.get_accounts(account_type="asset")
    assert all(a.type == "asset" for a in asset_accounts)
    assert len(asset_accounts) == 2  # assets, assets:cash


def test_invalid_root_rejected(storage):
    """Test that invalid account roots are rejected."""
    with pytest.raises(ValueError, match="Invalid account root"):
        storage.add(make_entry("Bad", "badroot:foo", "assets:cash", "100.00"))


def test_account_names_lowercased(storage):
    """Test that account names are stored lowercase."""
    storage.add(make_entry("Test", "Assets:Cash", "Income:Revenue", "100.00"))
    accounts = storage.get_accounts()
    names = [a.name for a in accounts]
    assert "assets:cash" in names
    assert "income:revenue" in names
