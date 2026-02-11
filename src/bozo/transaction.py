"""Transaction model and storage."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal


@dataclass
class Transaction:
    """Represents a financial transaction."""

    amount: Decimal
    description: str
    category: str
    timestamp: datetime
    id: int | None = field(default=None)

    def __post_init__(self):
        if isinstance(self.amount, (int, float)):
            self.amount = Decimal(str(self.amount))

    def to_dict(self) -> dict:
        """Convert transaction to dictionary."""
        return {
            "id": self.id,
            "amount": str(self.amount),
            "description": self.description,
            "category": self.category,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Transaction":
        """Create transaction from dictionary."""
        return cls(
            id=data.get("id"),
            amount=Decimal(data["amount"]),
            description=data["description"],
            category=data["category"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
        )
