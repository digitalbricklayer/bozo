"""Journal entry and line item models for double-entry accounting."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal


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
