from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class InventoryItem:
    """Data Transfer Object for inventory items in UI layer."""

    id: int
    item_type_id: int
    item_type_name: str  # From ItemType.name
    item_sub_type: str  # From ItemType.sub_type
    is_serialized: bool  # From ItemType.is_serialized
    quantity: int
    serial_number: Optional[str]
    location: Optional[str]
    condition: Optional[str]
    notes: Optional[str]
    details: Optional[str]  # From ItemType.details
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_db_models(cls, item, item_type):
        """Create InventoryItem from Item and ItemType models.

        Args:
            item: Item model instance
            item_type: ItemType model instance

        Returns:
            InventoryItem instance.
        """
        return cls(
            id=item.id,
            item_type_id=item.item_type_id,
            item_type_name=item_type.name,
            item_sub_type=item_type.sub_type or "",
            is_serialized=item_type.is_serialized,
            quantity=item.quantity,
            serial_number=item.serial_number,
            location=item.location or "",
            condition=item.condition or "",
            notes=item.notes or "",
            details=item_type.details or "",
            created_at=item.created_at,
            updated_at=item.updated_at
        )

    @property
    def display_name(self) -> str:
        """Get formatted display name."""
        if self.item_sub_type:
            return f"{self.item_type_name} - {self.item_sub_type}"
        return self.item_type_name

    @property
    def display_info(self) -> str:
        """Get detailed display info for list view."""
        parts = [self.display_name]
        if self.serial_number:
            parts.append(f"SN: {self.serial_number}")
        else:
            parts.append(f"Qty: {self.quantity}")
        if self.location:
            parts.append(f"@ {self.location}")
        return " | ".join(parts)

    # Legacy compatibility methods (for gradual migration)
    @property
    def item_type(self) -> str:
        """Legacy property for backward compatibility."""
        return self.item_type_name

    @property
    def sub_type(self) -> str:
        """Legacy property for backward compatibility."""
        return self.item_sub_type

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "item_type_id": self.item_type_id,
            "item_type_name": self.item_type_name,
            "item_sub_type": self.item_sub_type,
            "is_serialized": self.is_serialized,
            "quantity": self.quantity,
            "serial_number": self.serial_number,
            "location": self.location,
            "condition": self.condition,
            "notes": self.notes,
            "details": self.details,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
