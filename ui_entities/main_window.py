from PyQt6 import uic
from PyQt6.QtWidgets import QMainWindow, QMessageBox
from ui_entities.inventory_model import InventoryModel
from ui_entities.inventory_item import InventoryItem
from ui_entities.inventory_list_view import InventoryListView
from ui_entities.item_details_dialog import ItemDetailsDialog
from ui_entities.add_item_dialog import AddItemDialog
from ui_entities.translations import tr


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("ui/MainWindow.ui", self)

        self._setup_ui()
        self._setup_inventory_list()
        self._load_sample_data()
        self._connect_signals()

    def _setup_ui(self):
        """Set up UI with localized strings."""
        self.setWindowTitle(tr("app.title"))
        if hasattr(self, 'addButton'):
            self.addButton.setText(tr("main.add_item"))

    def _setup_inventory_list(self):
        """Replace the placeholder widget with the custom inventory list view."""
        self.inventory_model = InventoryModel(self)

        # Create the custom list view
        self.inventory_list = InventoryListView(self)
        self.inventory_list.setModel(self.inventory_model)

        # Replace the listView placeholder from UI file
        if hasattr(self, 'listView'):
            layout = self.listView.parent().layout()
            if layout:
                # Find and replace the widget in layout
                for i in range(layout.count()):
                    if layout.itemAt(i).widget() == self.listView:
                        layout.removeWidget(self.listView)
                        self.listView.deleteLater()
                        layout.insertWidget(i, self.inventory_list)
                        break
            else:
                # No layout - use geometry from placeholder
                self.inventory_list.setGeometry(self.listView.geometry())
                self.inventory_list.setParent(self.listView.parent())
                self.listView.deleteLater()

    def _load_sample_data(self):
        """Load sample inventory items for demonstration."""
        sample_items = [
            InventoryItem(id=1, item_type="Електроніка", sub_type="Ноутбук", quantity=5, serial_number="EL-001-2024"),
            InventoryItem(id=2, item_type="Електроніка", sub_type="Монітор", quantity=10, serial_number="EL-002-2024"),
            InventoryItem(id=3, item_type="Меблі", sub_type="Стіл", quantity=8, serial_number="FN-001-2024"),
            InventoryItem(id=4, item_type="Меблі", sub_type="Крісло", quantity=15, serial_number="FN-002-2024"),
            InventoryItem(id=5, item_type="Канцтовари", sub_type="Папір для принтера", quantity=100, serial_number="OS-001-2024"),
        ]

        for item in sample_items:
            self.inventory_model.add_item(item)

    def _connect_signals(self):
        """Connect signals to slots."""
        self.inventory_list.edit_requested.connect(self._on_edit_item)
        self.inventory_list.details_requested.connect(self._on_show_details)
        self.inventory_list.delete_requested.connect(self._on_delete_item)

        if hasattr(self, 'addButton'):
            self.addButton.clicked.connect(self._on_add_clicked)

    def _on_edit_item(self, row: int, item: InventoryItem):
        """Handle edit request for an inventory item."""
        QMessageBox.information(
            self,
            tr("dialog.edit.title"),
            f"{tr('field.type')}: {item.item_type}\n"
            f"{tr('field.subtype')}: {item.sub_type if item.sub_type else '-'}\n"
            f"{tr('field.quantity')}: {item.quantity}\n"
            f"{tr('field.serial_number')}: {item.serial_number if item.serial_number else '-'}"
        )

    def _on_show_details(self, row: int, item: InventoryItem):
        """Handle show details request for an inventory item."""
        dialog = ItemDetailsDialog(item, self)
        dialog.exec()

    def _on_delete_item(self, row: int, item: InventoryItem):
        """Handle delete request for an inventory item."""
        reply = QMessageBox.question(
            self,
            tr("dialog.confirm_delete.title"),
            f"{tr('message.confirm_delete')}\n\n"
            f"{tr('field.type')}: {item.item_type}\n"
            f"{tr('field.subtype')}: {item.sub_type if item.sub_type else '-'}\n"
            f"{tr('field.serial_number')}: {item.serial_number if item.serial_number else '-'}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.inventory_model.remove_item(row)

    def _on_add_clicked(self):
        """Handle add button click - open add item dialog."""
        dialog = AddItemDialog(self)
        if dialog.exec():
            new_item = dialog.get_item()
            if new_item:
                self.inventory_model.add_item(new_item)
