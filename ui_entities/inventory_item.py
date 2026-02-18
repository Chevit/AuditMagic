from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


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
            "details": self.details,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


@dataclass
class GroupedInventoryItem:
    """Aggregated inventory item grouped by ItemType.

    Represents all items of the same type as a single row in the list view.
    """

    item_type_id: int
    item_type_name: str
    item_sub_type: str
    is_serialized: bool
    details: str
    total_quantity: int  # Sum of all items' quantities
    item_count: int  # Number of individual Item records
    serial_numbers: List[str] = field(default_factory=list)  # All serial numbers
    item_ids: List[int] = field(default_factory=list)  # All Item IDs for this type
    created_at: Optional[datetime] = None  # Earliest created_at
    updated_at: Optional[datetime] = None  # Latest updated_at

    @classmethod
    def from_item_type_and_items(cls, item_type, items: list):
        """Create GroupedInventoryItem from ItemType and list of Items.

        Args:
            item_type: ItemType model instance
            items: List of Item model instances belonging to this type

        Returns:
            GroupedInventoryItem instance.
        """
        serial_numbers = [
            item.serial_number for item in items
            if item.serial_number
        ]
        item_ids = [item.id for item in items]
        total_quantity = sum(item.quantity for item in items)

        # Get earliest created_at and latest updated_at
        created_dates = [item.created_at for item in items if item.created_at]
        updated_dates = [item.updated_at for item in items if item.updated_at]

        return cls(
            item_type_id=item_type.id,
            item_type_name=item_type.name,
            item_sub_type=item_type.sub_type or "",
            is_serialized=item_type.is_serialized,
            details=item_type.details or "",
            total_quantity=total_quantity,
            item_count=len(items),
            serial_numbers=sorted(serial_numbers),
            item_ids=item_ids,
            created_at=min(created_dates) if created_dates else None,
            updated_at=max(updated_dates) if updated_dates else None,
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
        parts.append(f"Qty: {self.total_quantity}")
        if self.is_serialized and self.serial_numbers:
            parts.append(f"({len(self.serial_numbers)} SN)")
        return " | ".join(parts)

    # Legacy compatibility
    @property
    def item_type(self) -> str:
        return self.item_type_name

    @property
    def sub_type(self) -> str:
        return self.item_sub_type

    @property
    def quantity(self) -> int:
        return self.total_quantity

    @property
    def id(self) -> int:
        """Return first item ID for compatibility."""
        return self.item_ids[0] if self.item_ids else 0

    @property
    def serial_number(self) -> Optional[str]:
        """Return first serial number for compatibility, or None."""
        return self.serial_numbers[0] if self.serial_numbers else None

    @property
    def location(self) -> str:
        """Grouped items don't have a single location."""
        return ""

    @property
    def condition(self) -> str:
        """Grouped items don't have a single condition."""
        return ""

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "item_type_id": self.item_type_id,
            "item_type_name": self.item_type_name,
            "item_sub_type": self.item_sub_type,
            "is_serialized": self.is_serialized,
            "details": self.details,
            "total_quantity": self.total_quantity,
            "item_count": self.item_count,
            "serial_numbers": self.serial_numbers,
            "item_ids": self.item_ids,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
