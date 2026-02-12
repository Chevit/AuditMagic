from PyQt6 import uic
from PyQt6.QtWidgets import QMainWindow, QMessageBox, QVBoxLayout, QWidget
from ui_entities.inventory_model import InventoryModel
from ui_entities.inventory_item import InventoryItem
from ui_entities.inventory_list_view import InventoryListView
from ui_entities.item_details_dialog import ItemDetailsDialog
from ui_entities.add_item_dialog import AddItemDialog
from ui_entities.edit_item_dialog import EditItemDialog
from ui_entities.search_widget import SearchWidget
from ui_entities.quantity_dialog import QuantityDialog
from ui_entities.transactions_dialog import TransactionsDialog
from ui_entities.translations import tr
from db import init_database
from services import InventoryService, SearchService, TransactionService
from config import config
from logger import logger


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("ui/MainWindow.ui", self)

        # Initialize database
        init_database()

        self._setup_ui()
        self._setup_search_widget()
        self._setup_inventory_list()
        self._load_data_from_db()
        self._connect_signals()
        self._restore_window_state()

    def _setup_ui(self):
        """Set up UI with localized strings."""
        self.setWindowTitle(tr("app.title"))
        if hasattr(self, "addButton"):
            self.addButton.setText(tr("main.add_item"))

    def _setup_search_widget(self):
        """Set up the search widget above the list."""
        self.search_widget = SearchWidget(self)
        self.search_widget.set_autocomplete_callback(self._get_autocomplete_suggestions)
        self.search_widget.search_requested.connect(self._on_search)
        self.search_widget.search_cleared.connect(self._on_search_cleared)

    def _setup_inventory_list(self):
        """Replace the placeholder widget with the custom inventory list view."""
        self.inventory_model = InventoryModel(self)

        # Create the custom list view
        self.inventory_list = InventoryListView(self)
        self.inventory_list.setModel(self.inventory_model)

        # Replace the listView placeholder from UI file
        if hasattr(self, "listView"):
            layout = self.listView.parent().layout()
            if layout:
                # Find and replace the widget in layout
                for i in range(layout.count()):
                    if layout.itemAt(i).widget() == self.listView:
                        layout.removeWidget(self.listView)
                        self.listView.deleteLater()
                        # Insert search widget before the list
                        layout.insertWidget(i, self.search_widget)
                        layout.insertWidget(i + 1, self.inventory_list)
                        break
            else:
                # No layout - use geometry from placeholder
                self.inventory_list.setGeometry(self.listView.geometry())
                self.inventory_list.setParent(self.listView.parent())
                self.listView.deleteLater()

    def _load_data_from_db(self):
        """Load inventory items from database."""
        items = InventoryService.get_all_items()
        for item in items:
            self.inventory_model.add_item(item)

    def _connect_signals(self):
        """Connect signals to slots."""
        self.inventory_list.edit_requested.connect(self._on_edit_item)
        self.inventory_list.details_requested.connect(self._on_show_details)
        self.inventory_list.delete_requested.connect(self._on_delete_item)
        self.inventory_list.add_quantity_requested.connect(self._on_add_quantity)
        self.inventory_list.remove_quantity_requested.connect(self._on_remove_quantity)
        self.inventory_list.transactions_requested.connect(self._on_show_transactions)

        if hasattr(self, "addButton"):
            self.addButton.clicked.connect(self._on_add_clicked)

    def _on_edit_item(self, row: int, item: InventoryItem):
        """Handle edit request for an inventory item."""
        dialog = EditItemDialog(item, self)
        if dialog.exec():
            edited_item = dialog.get_item()
            edit_notes = dialog.get_edit_notes()
            if edited_item and item.id is not None:
                updated_item = InventoryService.edit_item(
                    item_id=item.id,
                    item_type=edited_item.item_type,
                    quantity=edited_item.quantity,
                    sub_type=edited_item.sub_type,
                    serial_number=edited_item.serial_number,
                    details=edited_item.details,
                    edit_reason=edit_notes,
                )
                if updated_item:
                    self.inventory_model.update_item(row, updated_item)

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
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            if item.id is not None:
                InventoryService.delete_item(item.id)
            self.inventory_model.remove_item(row)

    def _on_add_clicked(self):
        """Handle add button click - open add item dialog."""
        dialog = AddItemDialog(self)
        if dialog.exec():
            new_item = dialog.get_item()
            if new_item:
                # Save to database (merge with existing if same fields)
                saved_item, was_merged = InventoryService.create_or_merge_item(
                    item_type=new_item.item_type,
                    quantity=new_item.quantity,
                    sub_type=new_item.sub_type,
                    serial_number=new_item.serial_number,
                    details=new_item.details,
                )
                if was_merged:
                    # Update existing item in the list
                    self._update_item_in_model(saved_item)
                else:
                    # Add new item to the list
                    self.inventory_model.add_item(saved_item)

    def _update_item_in_model(self, item: InventoryItem):
        """Update an existing item in the model by ID."""
        for row in range(self.inventory_model.rowCount()):
            existing = self.inventory_model.get_item(row)
            if existing and existing.id == item.id:
                self.inventory_model.update_item(row, item)
                return
        # If not found in model (filtered view), refresh the list
        self._refresh_item_list()

    def _on_add_quantity(self, row: int, item: InventoryItem):
        """Handle add quantity request."""
        item_name = (
            f"{item.item_type} - {item.sub_type}" if item.sub_type else item.item_type
        )
        dialog = QuantityDialog(item_name, item.quantity, is_add=True, parent=self)
        if dialog.exec():
            quantity = dialog.get_quantity()
            notes = dialog.get_notes()
            if item.id is not None:
                updated_item = InventoryService.add_quantity(item.id, quantity, notes)
                if updated_item:
                    self.inventory_model.update_item(row, updated_item)

    def _on_remove_quantity(self, row: int, item: InventoryItem):
        """Handle remove quantity request."""
        item_name = (
            f"{item.item_type} - {item.sub_type}" if item.sub_type else item.item_type
        )
        dialog = QuantityDialog(item_name, item.quantity, is_add=False, parent=self)
        if dialog.exec():
            quantity = dialog.get_quantity()
            notes = dialog.get_notes()
            if item.id is not None:
                try:
                    updated_item = InventoryService.remove_quantity(
                        item.id, quantity, notes
                    )
                    if updated_item:
                        self.inventory_model.update_item(row, updated_item)
                except ValueError as e:
                    QMessageBox.warning(self, tr("message.validation_error"), str(e))

    def _on_show_transactions(self, row: int, item: InventoryItem):
        """Handle show transactions request."""
        item_name = (
            f"{item.item_type} - {item.sub_type}" if item.sub_type else item.item_type
        )
        dialog = TransactionsDialog(item_id=item.id, item_name=item_name, parent=self)
        dialog.set_transactions_callback(
            TransactionService.get_transactions_by_date_range
        )
        dialog.exec()

    def _get_autocomplete_suggestions(self, prefix: str, field: str) -> list:
        """Get autocomplete suggestions for search."""
        return SearchService.get_autocomplete_suggestions(
            prefix, field if field else None
        )

    def _on_search(self, query: str, field: str):
        """Handle search request."""
        field_value = field if field else None
        results = SearchService.search(query, field_value, save_to_history=False)
        self._display_search_results(results)

    def _on_search_cleared(self):
        """Handle search cleared - show all items."""
        self._refresh_item_list()

    def _display_search_results(self, items: list):
        """Display search results in the list."""
        self.inventory_model.clear()
        for item in items:
            self.inventory_model.add_item(item)

    def _refresh_item_list(self):
        """Refresh the item list from database."""
        self.inventory_model.clear()
        items = InventoryService.get_all_items()
        for item in items:
            self.inventory_model.add_item(item)

    def _restore_window_state(self):
        """Restore window size and position from config."""
        geometry = config.get("window.geometry")
        if geometry:
            self.restoreGeometry(bytes.fromhex(geometry))
            logger.debug("Window geometry restored from config")

        if config.get("window.maximized", False):
            self.showMaximized()
            logger.debug("Window maximized from config")

    def closeEvent(self, event):
        """Save window state before closing."""
        config.set(
            "window.geometry", self.saveGeometry().toHex().data().decode(), save=False
        )
        config.set("window.maximized", self.isMaximized(), save=False)
        config.save()
        logger.info("Window state saved to config")
        event.accept()
