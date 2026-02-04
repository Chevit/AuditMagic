from dataclasses import dataclass
from typing import Optional


@dataclass
class InventoryItem:
    """Data class representing an inventory item with type, sub-type, quantity, serial number, and notes."""
    item_type: str
    sub_type: str
    quantity: int
    serial_number: str
    notes: str = ""
    id: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'item_type': self.item_type,
            'sub_type': self.sub_type,
            'quantity': self.quantity,
            'serial_number': self.serial_number,
            'notes': self.notes
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'InventoryItem':
        return cls(
            id=data.get('id'),
            item_type=data.get('item_type', ''),
            sub_type=data.get('sub_type', ''),
            quantity=data.get('quantity', 0),
            serial_number=data.get('serial_number', ''),
            notes=data.get('notes', '')
        )

    @classmethod
    def from_db_model(cls, item) -> 'InventoryItem':
        """Create an InventoryItem from a database Item model."""
        return cls(
            id=item.id,
            item_type=item.item_type,
            sub_type=item.sub_type or "",
            quantity=item.quantity,
            serial_number=item.serial_number or "",
            notes=item.notes or ""
        )
