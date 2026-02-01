from typing import List, Optional
from PyQt6.QtCore import Qt, QAbstractListModel, QModelIndex
from ui_entities.inventory_item import InventoryItem


class InventoryItemRole:
    """Custom roles for accessing InventoryItem data."""
    ItemType = Qt.ItemDataRole.UserRole + 1
    SubType = Qt.ItemDataRole.UserRole + 2
    Quantity = Qt.ItemDataRole.UserRole + 3
    SerialNumber = Qt.ItemDataRole.UserRole + 4
    ItemData = Qt.ItemDataRole.UserRole + 5


class InventoryModel(QAbstractListModel):
    """Model for managing inventory items in a QListView."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items: List[InventoryItem] = []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._items)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._items)):
            return None

        item = self._items[index.row()]

        if role == Qt.ItemDataRole.DisplayRole:
            return f"{item.item_type} - {item.sub_type}"

        if role == InventoryItemRole.ItemType:
            return item.item_type

        if role == InventoryItemRole.SubType:
            return item.sub_type

        if role == InventoryItemRole.Quantity:
            return item.quantity

        if role == InventoryItemRole.SerialNumber:
            return item.serial_number

        if role == InventoryItemRole.ItemData:
            return item

        return None

    def setData(self, index: QModelIndex, value, role: int = Qt.ItemDataRole.EditRole) -> bool:
        if not index.isValid() or not (0 <= index.row() < len(self._items)):
            return False

        item = self._items[index.row()]

        if role == InventoryItemRole.ItemData and isinstance(value, InventoryItem):
            self._items[index.row()] = value
            self.dataChanged.emit(index, index)
            return True

        if role == InventoryItemRole.ItemType:
            item.item_type = value
        elif role == InventoryItemRole.SubType:
            item.sub_type = value
        elif role == InventoryItemRole.Quantity:
            item.quantity = value
        elif role == InventoryItemRole.SerialNumber:
            item.serial_number = value
        else:
            return False

        self.dataChanged.emit(index, index)
        return True

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    def add_item(self, item: InventoryItem) -> None:
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

    def get_item(self, row: int) -> Optional[InventoryItem]:
        """Get the inventory item at the given row."""
        if 0 <= row < len(self._items):
            return self._items[row]
        return None

    def update_item(self, row: int, item: InventoryItem) -> bool:
        """Update the inventory item at the given row."""
        if not (0 <= row < len(self._items)):
            return False
        self._items[row] = item
        index = self.index(row)
        self.dataChanged.emit(index, index)
        return True

    def clear(self) -> None:
        """Clear all items from the model."""
        self.beginResetModel()
        self._items.clear()
        self.endResetModel()

    def items(self) -> List[InventoryItem]:
        """Return a copy of all items."""
        return self._items.copy()
