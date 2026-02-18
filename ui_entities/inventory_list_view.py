from PyQt6.QtCore import QModelIndex, Qt, pyqtSignal
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QListView, QMenu

from ui_entities.inventory_delegate import InventoryItemDelegate
from ui_entities.translations import tr


class InventoryListView(QListView):
    """Custom QListView for displaying inventory items with context menu support."""

    # Signals use 'object' to support both InventoryItem and GroupedInventoryItem
    edit_requested = pyqtSignal(int, object)
    details_requested = pyqtSignal(int, object)
    delete_requested = pyqtSignal(int, object)
    add_quantity_requested = pyqtSignal(int, object)
    remove_quantity_requested = pyqtSignal(int, object)
    transactions_requested = pyqtSignal(int, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._setup_context_menu()

    def _setup_ui(self):
        """Configure the list view appearance and behavior."""
        self.setItemDelegate(InventoryItemDelegate(self))
        self.setMouseTracking(True)
        self.setSelectionMode(QListView.SelectionMode.SingleSelection)
        self.setVerticalScrollMode(QListView.ScrollMode.ScrollPerPixel)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setSpacing(0)
        self.setUniformItemSizes(True)

    def _setup_context_menu(self):
        """Set up the context menu with edit, details, and delete actions."""
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def _show_context_menu(self, position):
        """Show context menu at the given position."""
        index = self.indexAt(position)
        if not index.isValid():
            return

        row = index.row()
        item = self._get_item_from_index(index)
        if item is None:
            return

        menu = QMenu(self)

        edit_action = QAction(tr("menu.edit"), self)
        edit_action.triggered.connect(lambda: self.edit_requested.emit(row, item))
        menu.addAction(edit_action)

        details_action = QAction(tr("menu.details"), self)
        details_action.triggered.connect(lambda: self.details_requested.emit(row, item))
        menu.addAction(details_action)

        menu.addSeparator()

        # Quantity actions — dynamic labels for serialized items
        if item.is_serialized:
            add_qty_label = tr("menu.add_serial_number")
            remove_qty_label = tr("menu.remove_serial_number")
        else:
            add_qty_label = tr("menu.add_quantity")
            remove_qty_label = tr("menu.remove_quantity")

        add_qty_action = QAction(add_qty_label, self)
        add_qty_action.triggered.connect(
            lambda: self.add_quantity_requested.emit(row, item)
        )
        menu.addAction(add_qty_action)

        remove_qty_action = QAction(remove_qty_label, self)
        remove_qty_action.triggered.connect(
            lambda: self.remove_quantity_requested.emit(row, item)
        )
        menu.addAction(remove_qty_action)

        menu.addSeparator()

        # Transactions action
        transactions_action = QAction(tr("menu.transactions"), self)
        transactions_action.triggered.connect(
            lambda: self.transactions_requested.emit(row, item)
        )
        menu.addAction(transactions_action)

        menu.addSeparator()

        delete_action = QAction(tr("menu.delete"), self)
        delete_action.triggered.connect(lambda: self.delete_requested.emit(row, item))
        menu.addAction(delete_action)

        menu.exec(self.viewport().mapToGlobal(position))

    def mouseDoubleClickEvent(self, event):
        """Handle double-click to open details."""
        index = self.indexAt(event.pos())
        if index.isValid():
            row = index.row()
            item = self._get_item_from_index(index)
            if item is not None:
                self.details_requested.emit(row, item)
        super().mouseDoubleClickEvent(event)

    def _get_item_from_index(self, index: QModelIndex):
        """Get the item (InventoryItem or GroupedInventoryItem) from the model at the given index."""
        from ui_entities.inventory_model import InventoryItemRole

        return index.data(InventoryItemRole.ItemData)
