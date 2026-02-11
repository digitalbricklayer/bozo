"""Journal entry and line item models for double-entry accounting."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

ACCOUNT_TYPES = {
    "assets": "asset",
    "liabilities": "liability",
    "income": "income",
    "expenses": "expense",
    "capital": "capital",
    "drawings": "drawings",
}


def parse_account_path(name: str) -> tuple[str, list[str]]:
    """Split an account name on ':' and validate the root segment.

    Returns (type, segments). Raises ValueError for invalid roots.
    """
    segments = [s.strip() for s in name.lower().split(":")]
    if not segments or not segments[0]:
        raise ValueError(f"Invalid account name: '{name}'")
    root = segments[0]
    if root not in ACCOUNT_TYPES:
        valid = ", ".join(sorted(ACCOUNT_TYPES))
        raise ValueError(
            f"Invalid account root '{root}'. Must be one of: {valid}"
        )
    return ACCOUNT_TYPES[root], segments


@dataclass
class Account:
    """A ledger account in the chart of accounts."""

    name: str
    type: str
    parent_id: int | None = None
    id: int | None = None


@dataclass
class LineItem:
    """A single debit or credit line in a journal entry."""

    account: str
    debit: Decimal | None = None
    credit: Decimal | None = None
    id: int | None = None


@dataclass
class JournalEntry:
    """A double-entry journal entry with balanced debits and credits."""

    description: str
    timestamp: datetime
    line_items: list[LineItem] = field(default_factory=list)
    id: int | None = None
