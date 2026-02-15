from typing import List, Optional, Union

from PyQt6.QtCore import QAbstractListModel, QModelIndex, Qt

from ui_entities.inventory_item import GroupedInventoryItem, InventoryItem

# Type alias for items that can be displayed in the list
DisplayItem = Union[InventoryItem, GroupedInventoryItem]


class InventoryItemRole:
    """Custom roles for accessing InventoryItem data."""

    ItemType = Qt.ItemDataRole.UserRole + 1
    SubType = Qt.ItemDataRole.UserRole + 2
    Quantity = Qt.ItemDataRole.UserRole + 3
    SerialNumber = Qt.ItemDataRole.UserRole + 4
    ItemData = Qt.ItemDataRole.UserRole + 5
    Details = Qt.ItemDataRole.UserRole + 6
    SerialNumbers = Qt.ItemDataRole.UserRole + 7  # List of serial numbers for grouped items
    IsSerialized = Qt.ItemDataRole.UserRole + 8
    ItemTypeId = Qt.ItemDataRole.UserRole + 9


class InventoryModel(QAbstractListModel):
    """Model for managing inventory items in a QListView.

    Supports both InventoryItem (individual items) and GroupedInventoryItem (aggregated by type).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items: List[DisplayItem] = []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._items)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._items)):
            return None

        item = self._items[index.row()]
        is_grouped = isinstance(item, GroupedInventoryItem)

        if role == Qt.ItemDataRole.DisplayRole:
            return item.display_name

        if role == InventoryItemRole.ItemType:
            return item.item_type

        if role == InventoryItemRole.SubType:
            return item.sub_type

        if role == InventoryItemRole.Quantity:
            return item.quantity

        if role == InventoryItemRole.SerialNumber:
            # For grouped items, return comma-separated serial numbers or None
            if is_grouped:
                return ", ".join(item.serial_numbers) if item.serial_numbers else None
            return item.serial_number

        if role == InventoryItemRole.SerialNumbers:
            # Return list of serial numbers (only for grouped items)
            if is_grouped:
                return item.serial_numbers
            return [item.serial_number] if item.serial_number else []

        if role == InventoryItemRole.ItemData:
            return item

        if role == InventoryItemRole.Details:
            return item.details

        if role == InventoryItemRole.IsSerialized:
            return item.is_serialized

        if role == InventoryItemRole.ItemTypeId:
            return item.item_type_id

        return None

    def setData(
        self, index: QModelIndex, value, role: int = Qt.ItemDataRole.EditRole
    ) -> bool:
        if not index.isValid() or not (0 <= index.row() < len(self._items)):
            return False

        item = self._items[index.row()]

        # Only allow replacing the entire item data
        # Direct field editing is not supported for GroupedInventoryItem
        if role == InventoryItemRole.ItemData:
            self._items[index.row()] = value
            self.dataChanged.emit(index, index)
            return True

        # For InventoryItem only, allow direct field modification
        if isinstance(item, InventoryItem):
            if role == InventoryItemRole.Quantity:
                # InventoryItem is a dataclass, we need to create a new instance
                # For now, just signal that the data changed (actual edits go through dialogs)
                pass
            self.dataChanged.emit(index, index)
            return True

        return False

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    def add_item(self, item: DisplayItem) -> None:
        """Add a new inventory item to the model."""
        row = len(self._items)
        self.beginInsertRows(QModelIndex(), row, row)
        self._items.append(item)
        self.endInsertRows()

    def remove_item(self, row: int) -> bool:
        """Remove an inventory item at the given row."""
        if not (0 <= row < len(self._items)):
            return False
        self.beginRemoveRows(QModelIndex(), row, row)
        del self._items[row]
        self.endRemoveRows()
        return True

    def get_item(self, row: int) -> Optional[DisplayItem]:
        """Get the inventory item at the given row."""
        if 0 <= row < len(self._items):
            return self._items[row]
        return None

    def update_item(self, row: int, item: DisplayItem) -> bool:
        """Update the inventory item at the given row."""
        if not (0 <= row < len(self._items)):
            return False
        self._items[row] = item
        index = self.index(row)
        self.dataChanged.emit(index, index)
        return True

    def find_by_type_id(self, item_type_id: int) -> Optional[int]:
        """Find row index by item type ID."""
        for row, item in enumerate(self._items):
            if item.item_type_id == item_type_id:
                return row
        return None

    def clear(self) -> None:
        """Clear all items from the model."""
        self.beginResetModel()
        self._items.clear()
        self.endResetModel()

    def items(self) -> List[DisplayItem]:
        """Return a copy of all items."""
        return self._items.copy()
