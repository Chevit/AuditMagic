from dataclasses import dataclass
from typing import Optional


@dataclass
class InventoryItem:
    """Data class representing an inventory item with type, sub-type, quantity, and serial number."""
    item_type: str
    sub_type: str
    quantity: int
    serial_number: str
    id: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'item_type': self.item_type,
            'sub_type': self.sub_type,
            'quantity': self.quantity,
            'serial_number': self.serial_number
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'InventoryItem':
        return cls(
            id=data.get('id'),
            item_type=data.get('item_type', ''),
            sub_type=data.get('sub_type', ''),
            quantity=data.get('quantity', 0),
            serial_number=data.get('serial_number', '')
        )
