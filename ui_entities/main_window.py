from PyQt6 import uic
from PyQt6.QtGui import QAction, QActionGroup
from PyQt6.QtWidgets import (
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from config import config
from db import init_database
from logger import logger
from services import InventoryService, SearchService, TransactionService
from styles import apply_button_style
from theme_manager import get_theme_manager
from ui_entities.add_item_dialog import AddItemDialog
from ui_entities.edit_item_dialog import EditItemDialog
from ui_entities.inventory_item import GroupedInventoryItem, InventoryItem
from ui_entities.inventory_list_view import InventoryListView
from ui_entities.inventory_model import InventoryModel
from ui_entities.item_details_dialog import ItemDetailsDialog
from ui_entities.quantity_dialog import QuantityDialog
from ui_entities.search_widget import SearchWidget
from ui_entities.transactions_dialog import TransactionsDialog
from ui_entities.translations import tr


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("ui/MainWindow.ui", self)

        # Initialize database
        init_database()

        self._setup_ui()
        self._setup_theme_menu()
        self._setup_search_widget()
        self._setup_inventory_list()
        self._load_data_from_db()
        self._connect_signals()
        self._restore_window_state()

    def _setup_ui(self):
        """Set up UI with localized strings and apply theme-aware styles."""
        self.setWindowTitle(tr("app.title"))
        if hasattr(self, "addButton"):
            self.addButton.setText(tr("main.add_item"))
            apply_button_style(self.addButton, "primary")

    def _setup_theme_menu(self):
        """Set up theme switching menu."""
        from theme_config import Theme

        # Create menu bar if it doesn't exist
        menu_bar = self.menuBar()

        # Create Theme menu
        theme_menu = menu_bar.addMenu("🎨 " + tr("menu.theme"))

        # Get all available themes
        theme_names = Theme.get_all_names()
        current_theme = get_theme_manager().get_current_theme()

        # Create action group for radio button behavior
        theme_action_group = QActionGroup(self)
        theme_action_group.setExclusive(True)

        # Add action for each theme
        for theme_name in theme_names:
            action = QAction(theme_name, self)
            action.setCheckable(True)
            action.setActionGroup(theme_action_group)
            action.triggered.connect(
                lambda checked, name=theme_name: self._on_theme_changed(name)
            )
            theme_menu.addAction(action)

            # Set current theme as checked
            if theme_name == current_theme.value.name:
                action.setChecked(True)

        logger.info("Theme menu created")

    def _on_theme_changed(self, theme_name: str):
        """Handle theme change."""
        from theme_config import Theme

        theme_manager = get_theme_manager()
        if theme_manager:
            try:
                theme = Theme.get_by_name(theme_name)
                theme_manager.apply_theme(theme)

                # Save to config
                config.set("theme", theme_name)

                # Refresh search widget styles to match new theme
                if hasattr(self, "search_widget"):
                    self._reapply_search_widget_styles()

                logger.info(f"Theme changed to: {theme_name}")

                # Show message
                QMessageBox.information(
                    self,
                    tr("message.theme.changed"),
                    tr("message.theme.changed.text"),
                )
            except ValueError:
                logger.error(f"Invalid theme: {theme_name}")
                QMessageBox.warning(
                    self,
                    "Error",
                    f"Invalid theme: {theme_name}",
                )

    def _setup_search_widget(self):
        """Set up the search widget above the list."""
        self.search_widget = SearchWidget(self)
        self.search_widget.set_autocomplete_callback(self._get_autocomplete_suggestions)
        self.search_widget.search_requested.connect(self._on_search)
        self.search_widget.search_cleared.connect(self._on_search_cleared)

    def _reapply_search_widget_styles(self):
        """Reapply styles to SearchWidget after adding to layout."""
        from styles import apply_button_style, apply_combo_box_style, apply_input_style

        # Reapply styles to ensure they override qt-material
        apply_combo_box_style(self.search_widget.field_combo)
        apply_input_style(self.search_widget.search_input)
        apply_button_style(self.search_widget.search_button, "info")
        apply_button_style(self.search_widget.clear_button, "secondary")

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
                        # Reapply styles after adding to layout (in case qt-material overrides)
                        self._reapply_search_widget_styles()
                        break
            else:
                # No layout - use geometry from placeholder
                self.inventory_list.setGeometry(self.listView.geometry())
                self.inventory_list.setParent(self.listView.parent())
                self.listView.deleteLater()

    def _load_data_from_db(self):
        """Load inventory items from database (grouped by type)."""
        items = InventoryService.get_all_items_grouped()
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

    def _on_edit_item(self, row: int, item):
        """Handle edit request for an inventory item."""
        from repositories import ItemRepository

        is_grouped = isinstance(item, GroupedInventoryItem)

        dialog = EditItemDialog(item, self)
        if dialog.exec():
            edited_item = dialog.get_item()
            edit_notes = dialog.get_edit_notes()
            deleted_serials = dialog.get_deleted_serial_numbers()

            # Determine the item ID to edit (before any deletions)
            item_id = None
            existing_serial = None
            if is_grouped:
                if item.is_serialized:
                    # Pick the first remaining serial (deterministic via sorted list)
                    remaining_serials = [
                        sn for sn in item.serial_numbers if sn not in deleted_serials
                    ]
                    if remaining_serials:
                        db_item = ItemRepository.search_by_serial(remaining_serials[0])
                        if db_item:
                            item_id = db_item.id
                            existing_serial = db_item.serial_number
                else:
                    item_id = item.item_ids[0] if item.item_ids else None
            else:
                item_id = item.id

            # Edit the item first (validates at DB level before we delete anything)
            edit_succeeded = False
            if edited_item and item_id is not None:
                serial_to_use = existing_serial if existing_serial else (edited_item.serial_number or "")

                try:
                    updated_item = InventoryService.edit_item(
                        item_id=item_id,
                        item_type_name=edited_item.item_type_name,
                        sub_type=edited_item.item_sub_type,
                        quantity=edited_item.quantity,
                        is_serialized=edited_item.is_serialized,
                        serial_number=serial_to_use,
                        details=edited_item.details or "",
                        location=edited_item.location or "",
                        condition=edited_item.condition or "",
                        notes=edited_item.notes or "",
                        edit_reason=edit_notes,
                    )
                    if updated_item:
                        edit_succeeded = True
                except Exception as e:
                    logger.error(f"Failed to edit item: {e}")
                    QMessageBox.warning(
                        self,
                        tr("error.generic.title"),
                        f"{tr('error.generic.message')}\n{e}",
                    )
                    return

            # Only delete serial numbers after edit succeeds
            if deleted_serials:
                try:
                    deleted_count = InventoryService.delete_items_by_serial_numbers(deleted_serials)
                    logger.info(f"Deleted {deleted_count} items with serial numbers")
                except Exception as e:
                    logger.error(f"Failed to delete serial numbers: {e}")
                    QMessageBox.warning(
                        self,
                        tr("error.generic.title"),
                        f"{tr('error.generic.message')}\n{e}",
                    )

            if edit_succeeded or deleted_serials:
                self._refresh_item_list()

    def _on_show_details(self, row: int, item):
        """Handle show details request for an inventory item."""
        dialog = ItemDetailsDialog(item, self)
        dialog.exec()

    def _on_delete_item(self, row: int, item):
        """Handle delete request for an inventory item."""
        is_grouped = isinstance(item, GroupedInventoryItem)

        # Build confirmation message
        if is_grouped:
            qty_info = f"{tr('field.quantity')}: {item.total_quantity}"
            if item.serial_numbers:
                qty_info += f" ({len(item.serial_numbers)} {tr('label.serial_number')})"
        else:
            qty_info = f"{tr('field.serial_number')}: {item.serial_number if item.serial_number else '-'}"

        reply = QMessageBox.question(
            self,
            tr("dialog.confirm_delete.title"),
            f"{tr('message.confirm_delete')}\n\n"
            f"{tr('field.type')}: {item.item_type}\n"
            f"{tr('field.subtype')}: {item.sub_type if item.sub_type else '-'}\n"
            f"{qty_info}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            if is_grouped:
                # Delete all items for this type
                for item_id in item.item_ids:
                    InventoryService.delete_item(item_id)
            elif item.id is not None:
                InventoryService.delete_item(item.id)
            self.inventory_model.remove_item(row)

    def _on_add_clicked(self):
        """Handle add button click - open add item dialog."""
        dialog = AddItemDialog(self)
        if dialog.exec():
            new_item = dialog.get_item()
            if new_item:
                # Item is already saved by the dialog via InventoryService.create_item
                # Refresh the list to show grouped items correctly
                self._refresh_item_list()

    def _update_item_in_model(self, item: InventoryItem):
        """Update an existing item in the model by ID."""
        for row in range(self.inventory_model.rowCount()):
            existing = self.inventory_model.get_item(row)
            if existing and existing.id == item.id:
                self.inventory_model.update_item(row, item)
                return
        # If not found in model (filtered view), refresh the list
        self._refresh_item_list()

    def _on_add_quantity(self, row: int, item):
        """Handle add quantity request."""
        is_grouped = isinstance(item, GroupedInventoryItem)

        # For serialized items, adding quantity requires a new serial number
        if item.is_serialized:
            QMessageBox.information(
                self,
                tr("dialog.add_quantity.title"),
                tr("message.serialized_use_add_item"),
            )
            return

        item_name = (
            f"{item.item_type} - {item.sub_type}" if item.sub_type else item.item_type
        )
        dialog = QuantityDialog(item_name, item.quantity, is_add=True, parent=self)
        if dialog.exec():
            quantity = dialog.get_quantity()
            notes = dialog.get_notes()
            # For grouped items, use the first item ID
            item_id = item.item_ids[0] if is_grouped else item.id
            if item_id is not None:
                updated_item = InventoryService.add_quantity(item_id, quantity, notes)
                if updated_item:
                    self._refresh_item_list()

    def _on_remove_quantity(self, row: int, item):
        """Handle remove quantity request."""
        is_grouped = isinstance(item, GroupedInventoryItem)

        # For serialized items, removing means deleting the item
        if item.is_serialized:
            QMessageBox.information(
                self,
                tr("dialog.remove_quantity.title"),
                tr("message.serialized_use_delete"),
            )
            return

        item_name = (
            f"{item.item_type} - {item.sub_type}" if item.sub_type else item.item_type
        )
        dialog = QuantityDialog(item_name, item.quantity, is_add=False, parent=self)
        if dialog.exec():
            quantity = dialog.get_quantity()
            notes = dialog.get_notes()
            # For grouped items, use the first item ID
            item_id = item.item_ids[0] if is_grouped else item.id
            if item_id is not None:
                try:
                    updated_item = InventoryService.remove_quantity(
                        item_id, quantity, notes
                    )
                    if updated_item:
                        self._refresh_item_list()
                except ValueError as e:
                    QMessageBox.warning(self, tr("message.validation_error"), str(e))

    def _on_show_transactions(self, row: int, item):
        """Handle show transactions request."""
        is_grouped = isinstance(item, GroupedInventoryItem)
        item_name = (
            f"{item.item_type} - {item.sub_type}" if item.sub_type else item.item_type
        )
        # For grouped items, use the first item ID (transactions are per-item)
        item_id = item.item_ids[0] if is_grouped else item.id
        dialog = TransactionsDialog(item_id=item_id, item_name=item_name, parent=self)
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
        """Refresh the item list from database (grouped by type)."""
        self.inventory_model.clear()
        items = InventoryService.get_all_items_grouped()
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
