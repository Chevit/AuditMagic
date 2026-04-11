import sys
from typing import Optional

from PyQt6 import uic
from runtime import resource_path
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QAction, QActionGroup, QShowEvent
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSpacerItem,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.config import config
from core.db import init_database
from core.logger import logger
from core.repositories import LocationRepository
from core.services import InventoryService, SearchService, TransactionService
from ui.styles import apply_button_style, apply_combo_box_style, apply_input_style
from ui.theme_manager import get_theme_manager
from ui.dialogs.add_item_dialog import AddItemDialog
from ui.dialogs.add_serial_number_dialog import AddSerialNumberDialog
from ui.dialogs.remove_serial_number_dialog import RemoveSerialNumberDialog
from ui.dialogs.edit_item_dialog import EditItemDialog
from ui.models.inventory_item import GroupedInventoryItem, InventoryItem
from ui.widgets.inventory_list_view import InventoryListView
from ui.models.inventory_model import InventoryModel
from ui.dialogs.item_details_dialog import ItemDetailsDialog
from ui.dialogs.all_transactions_dialog import AllTransactionsDialog
from ui.dialogs.first_location_dialog import FirstLocationDialog
from ui.dialogs.location_management_dialog import LocationManagementDialog
from ui.widgets.location_selector import LocationSelectorWidget
from ui.dialogs.transfer_dialog import TransferDialog
from ui.dialogs.quantity_dialog import QuantityDialog
from ui.widgets.search_widget import SearchWidget
from ui.dialogs.transactions_dialog import TransactionsDialog
from ui.translations import tr


class MainWindow(QMainWindow):
    def __init__(self):
        # _current_location_id must be set before any method that may read it
        self._current_location_id: Optional[int] = None
        self._shown_once: bool = False

        super().__init__()
        uic.loadUi(resource_path("src/ui/forms/MainWindow.ui"), self)

        # Initialize database
        init_database()

        # 1. Restore last-selected location from core.config (three-case sentinel logic)
        # NOTE: _ensure_location_exists() is deferred to _deferred_first_show() via
        # showEvent so that the first-location wizard appears after the splash closes.
        self._init_current_location()

        # 3. Integrity check: auto-assign any NULL-location items
        self._check_unassigned_items()

        # 4. Set up UI components
        self._setup_ui()
        self._setup_file_menu()
        self._setup_theme_menu()
        self._setup_location_selector()
        self._setup_search_widget()
        self._setup_inventory_list()

        # 5. Restore location selector to current location (no signal emission)
        self.location_selector.set_current_location(self._current_location_id)

        # 6. Load data filtered by current location
        self._load_data_from_db()

        # 7. Connect all signals and restore window
        self._connect_signals()
        self._restore_window_state()

    def showEvent(self, event: QShowEvent) -> None:
        """On first show, defer the first-location wizard to after the splash closes."""
        super().showEvent(event)
        if not self._shown_once:
            self._shown_once = True
            QTimer.singleShot(0, self._deferred_first_show)

    def _deferred_first_show(self) -> None:
        """Run first-location wizard if needed, then sync location state.

        Scheduled by showEvent so this executes after window.show() and
        _splash_close() have both returned — making the wizard visible.
        Only re-syncs location state when the wizard actually ran (fresh install).
        """
        no_locations = LocationRepository.get_count() == 0
        self._ensure_location_exists()
        if no_locations:
            # Wizard just completed — sync location state and reload UI
            self._init_current_location()
            self.location_selector.refresh_locations()
            self.location_selector.set_current_location(self._current_location_id)
            self._load_data_from_db()

    def _setup_ui(self):
        """Set up UI with localized strings and apply theme-aware styles."""
        self.setWindowTitle(tr("app.title"))
        if hasattr(self, "addButton"):
            self.addButton.setText(tr("main.add_item"))
            apply_button_style(self.addButton, "primary")

        # Add "All Transactions" button to the bottom bar (right of the spacer)
        if hasattr(self, "horizontalLayout"):
            self.all_transactions_btn = QPushButton(tr("button.all_transactions"))
            apply_button_style(self.all_transactions_btn, "info")
            self.horizontalLayout.addWidget(self.all_transactions_btn)

    def _setup_file_menu(self) -> None:
        """Set up File menu with export action."""
        file_menu = self.menuBar().addMenu(tr("export.menu.file"))
        export_action = file_menu.addAction(tr("export.action"))
        export_action.triggered.connect(self._on_export_excel)

    def _on_export_excel(self) -> None:
        """Handle File → Export to Excel…"""
        import re
        from datetime import date

        from PyQt6.QtWidgets import QDialog, QFileDialog, QMessageBox

        from core.export_service import ExportService
        from core.repositories import LocationRepository
        from core.services import InventoryService, TransactionService
        from ui.dialogs.export_options_dialog import ExportOptionsDialog

        # Determine current location name
        current_loc_id = self._current_location_id  # None means "All Locations"
        if current_loc_id is not None:
            loc = LocationRepository.get_by_id(current_loc_id)
            location_name = loc.name if loc else tr("location.all")
        else:
            location_name = tr("location.all")

        # Guard: no items in the current view
        items = self.inventory_model.items()
        if not items:
            QMessageBox.warning(
                self,
                tr("export.dialog.title"),
                tr("export.error.no_items"),
            )
            return

        # Export options dialog
        has_filter = bool(self.search_widget.get_current_query())
        dlg = ExportOptionsDialog(
            location_name=location_name,
            has_active_filter=has_filter,
            parent=self,
        )
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        # Build suggested filename
        safe_loc = re.sub(r"[^\w\-]", "_", location_name)
        today = date.today().strftime("%Y-%m-%d")
        suggested = tr("export.filename_default").format(location=safe_loc, date=today)

        # Save As dialog
        path, _ = QFileDialog.getSaveFileName(
            self,
            tr("export.dialog.title"),
            suggested,
            "Excel Files (*.xlsx)",
        )
        if not path:
            return  # user cancelled

        # Load transactions if requested
        transactions = None
        loc_map = None
        type_map = None
        if dlg.include_transactions():
            scope = dlg.transaction_scope()
            if scope == "filtered":
                type_ids = list({item.item_type_id for item in items})
                transactions = TransactionService.get_for_export(
                    location_id=current_loc_id, item_type_ids=type_ids
                )
            else:
                transactions = TransactionService.get_for_export(location_id=current_loc_id)
            loc_map = {loc.id: loc.name for loc in LocationRepository.get_all()}
            type_map = InventoryService.get_item_type_display_names()

        # Build and save workbook
        try:
            wb = ExportService.build_workbook(
                items=items,
                location_name=location_name,
                transactions=transactions,
                loc_map=loc_map,
                type_map=type_map,
            )
            wb.save(path)
        except PermissionError:
            QMessageBox.critical(
                self,
                tr("export.dialog.title"),
                tr("export.error.permission"),
            )
            return
        except Exception as e:
            logger.error(f"Export failed: {e}", exc_info=True)
            QMessageBox.critical(self, tr("export.dialog.title"), str(e))
            return

        QMessageBox.information(
            self,
            tr("export.success.title"),
            tr("export.success.message").format(path=path),
        )

    def _setup_theme_menu(self):
        """Set up theme switching menu."""
        from ui.theme_config import Theme

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
        from ui.theme_config import Theme

        theme_manager = get_theme_manager()
        if theme_manager:
            try:
                theme = Theme.get_by_name(theme_name)
                theme_manager.apply_theme(theme)

                # Save to config
                config.set("theme", theme_name)

                # Refresh all widget styles to match new theme
                if hasattr(self, "search_widget") and hasattr(self, "location_selector"):
                    self._reapply_all_styles()

                logger.info(f"Theme changed to: {theme_name}")
            except ValueError:
                logger.error(f"Invalid theme: {theme_name}")
                QMessageBox.warning(
                    self,
                    "Error",
                    f"Invalid theme: {theme_name}",
                )

    # ------------------------------------------------------------------ #
    #  Location infrastructure                                            #
    # ------------------------------------------------------------------ #

    def _ensure_location_exists(self):
        """Show the first-launch wizard if no locations exist yet.

        If the user cancels without creating a location they are prompted to
        exit the application, since at least one location is required.
        """
        if LocationRepository.get_count() > 0:
            return
        while LocationRepository.get_count() == 0:
            dlg = FirstLocationDialog(self)
            dlg.exec()
            new_id = dlg.get_location_id()
            if new_id is not None:
                self._current_location_id = new_id
                break
            # User closed the dialog without creating a location.
            # A location is required — ask whether to exit.
            answer = QMessageBox.question(
                self,
                tr("location.required.title"),
                tr("location.required.message"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if answer == QMessageBox.StandardButton.Yes:
                sys.exit(0)

    def _init_current_location(self):
        """Restore the last-selected location from core.config (sentinel pattern).

        Three cases:
          - Key absent  → first launch or legacy config → default to first location.
          - Key = null  → user explicitly chose "All Locations" → keep None.
          - Key = int   → validate the location still exists; fall back to first if gone.
        """
        _MISSING = object()
        saved = config.get("ui.last_location_id", _MISSING)

        if saved is _MISSING:
            locs = LocationRepository.get_all()
            self._current_location_id = locs[0].id if locs else None
        elif saved is None:
            self._current_location_id = None
        else:
            loc = LocationRepository.get_by_id(int(saved))
            if loc:
                self._current_location_id = loc.id
            else:
                locs = LocationRepository.get_all()
                self._current_location_id = locs[0].id if locs else None

    def _check_unassigned_items(self):
        """If any items have no location, offer to assign them to a location."""
        count = LocationRepository.get_unassigned_item_count()
        if count == 0:
            return
        locs = LocationRepository.get_all()
        if not locs:
            return
        target_id = self._current_location_id or locs[0].id
        target_name = next((l.name for l in locs if l.id == target_id), locs[0].name)
        reply = QMessageBox.question(
            self,
            tr("location.unassigned.title"),
            tr("location.unassigned.message").format(count=count, location=target_name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            LocationRepository.assign_all_unassigned(target_id)

    def _setup_location_selector(self):
        """Create the LocationSelectorWidget (inserted into the layout later)."""
        self.location_selector = LocationSelectorWidget(self)

    def _on_location_changed(self, location_id):
        """Handle location dropdown change — save to config and reload list."""
        self._current_location_id = location_id
        config.set("ui.last_location_id", location_id)
        # Show "Search all locations" checkbox only when a specific location is active
        if hasattr(self, "search_widget"):
            self.search_widget.set_all_locations_visible(location_id is not None)
        self._refresh_item_list()

    def _on_manage_locations(self):
        """Open the location management dialog and reconcile state afterwards."""
        dlg = LocationManagementDialog(self)
        dlg.exec()

        self.location_selector.refresh_locations()

        # If the active location was deleted, fall back to first available
        if self._current_location_id is not None:
            loc = LocationRepository.get_by_id(self._current_location_id)
            if not loc:
                locs = LocationRepository.get_all()
                self._current_location_id = locs[0].id if locs else None
                self.location_selector.set_current_location(self._current_location_id)
                config.set("ui.last_location_id", self._current_location_id)

        # Safety net: if somehow all locations were deleted, re-run wizard
        if LocationRepository.get_count() == 0:
            self._ensure_location_exists()
            self.location_selector.refresh_locations()

        self._refresh_item_list()

    # ------------------------------------------------------------------ #

    def _setup_search_widget(self):
        """Set up the search widget above the list."""
        self.search_widget = SearchWidget(self)
        self.search_widget.set_autocomplete_callback(self._get_autocomplete_suggestions)
        self.search_widget.search_requested.connect(self._on_search)
        self.search_widget.search_cleared.connect(self._on_search_cleared)

    def _reapply_all_styles(self):
        """Re-apply theme-aware styles to all main-window widgets after a theme switch."""
        # Search widget
        apply_combo_box_style(self.search_widget.field_combo)
        apply_input_style(self.search_widget.search_input)
        apply_button_style(self.search_widget.search_button, "info")
        apply_button_style(self.search_widget.clear_button, "secondary")

        # Location selector
        self.location_selector.reapply_styles()

        # Main action buttons
        if hasattr(self, "addButton"):
            apply_button_style(self.addButton, "primary")
        if hasattr(self, "all_transactions_btn"):
            apply_button_style(self.all_transactions_btn, "info")

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
                        # Insert location selector, then search widget, then list
                        layout.insertWidget(i, self.location_selector)
                        layout.insertWidget(i + 1, self.search_widget)
                        layout.insertWidget(i + 2, self.inventory_list)
                        # Reapply styles after adding to layout (in case qt-material overrides)
                        self._reapply_all_styles()
                        break
            else:
                # No layout - use geometry from placeholder
                self.inventory_list.setGeometry(self.listView.geometry())
                self.inventory_list.setParent(self.listView.parent())
                self.listView.deleteLater()

    def _load_data_from_db(self):
        """Load inventory items from database (grouped by type, filtered by location)."""
        items = InventoryService.get_all_items_grouped(location_id=self._current_location_id)
        for item in items:
            self.inventory_model.add_item(item)

    def _connect_signals(self):
        """Connect signals to slots."""
        self.location_selector.location_changed.connect(self._on_location_changed)
        self.location_selector.manage_requested.connect(self._on_manage_locations)

        self.inventory_list.edit_requested.connect(self._on_edit_item)
        self.inventory_list.details_requested.connect(self._on_show_details)
        self.inventory_list.delete_requested.connect(self._on_delete_item)
        self.inventory_list.add_quantity_requested.connect(self._on_add_quantity)
        self.inventory_list.remove_quantity_requested.connect(self._on_remove_quantity)
        self.inventory_list.transactions_requested.connect(self._on_show_transactions)
        self.inventory_list.transfer_requested.connect(self._on_transfer_item)

        if hasattr(self, "addButton"):
            self.addButton.clicked.connect(self._on_add_clicked)
        if hasattr(self, "all_transactions_btn"):
            self.all_transactions_btn.clicked.connect(self._on_show_all_transactions)

    def _on_edit_item(self, row: int, item):
        """Handle edit request for an inventory item."""
        from core.repositories import ItemRepository

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
                        location_id=edited_item.location_id,
                        condition=edited_item.condition or "",
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
                    deleted_count = InventoryService.delete_items_by_serial_numbers(deleted_serials, edit_notes)
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
            try:
                if is_grouped:
                    # Delete the entire ItemType (cascades to all items + transactions)
                    InventoryService.delete_item_type(item.item_type_id)
                elif item.id is not None:
                    InventoryService.delete_item(item.id)
                self.inventory_model.remove_item(row)
            except Exception as e:
                logger.error(f"Failed to delete item: {e}")
                QMessageBox.warning(
                    self,
                    tr("error.generic.title"),
                    f"{tr('error.generic.message')}\n{e}",
                )

    def _on_add_clicked(self):
        """Handle add button click - open add item dialog."""
        dialog = AddItemDialog(current_location_id=self._current_location_id, parent=self)
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

        # For serialized items, open Add Serial Number dialog
        if item.is_serialized:
            existing_serials = item.serial_numbers if is_grouped else (
                [item.serial_number] if item.serial_number else []
            )
            dialog = AddSerialNumberDialog(
                item_type_name=item.item_type,
                sub_type=item.sub_type or "",
                existing_serials=existing_serials,
                current_location_id=self._current_location_id,
                parent=self,
            )
            if dialog.exec():
                try:
                    new_item = InventoryService.create_serialized_item(
                        item_type_name=item.item_type,
                        item_sub_type=item.sub_type or "",
                        serial_number=dialog.get_serial_number(),
                        location_id=dialog.get_location_id(),
                        notes=dialog.get_notes(),
                    )
                    if new_item:
                        self._refresh_item_list()
                except ValueError as e:
                    QMessageBox.warning(self, tr("message.validation_error"), str(e))
            return

        item_name = (
            f"{item.item_type} - {item.sub_type}" if item.sub_type else item.item_type
        )
        # For grouped items, use the total_quantity already present in the DTO
        target_item_id = item.item_ids[0] if is_grouped else item.id
        actual_quantity = item.total_quantity if is_grouped else item.quantity
        dialog = QuantityDialog(item_name, actual_quantity, is_add=True, parent=self)
        if dialog.exec():
            quantity = dialog.get_quantity()
            notes = dialog.get_notes()
            if target_item_id is not None:
                updated_item = InventoryService.add_quantity(target_item_id, quantity, notes)
                if updated_item:
                    self._refresh_item_list()

    def _on_remove_quantity(self, row: int, item):
        """Handle remove quantity request."""
        is_grouped = isinstance(item, GroupedInventoryItem)

        # For serialized items, open Remove Serial Number dialog
        if item.is_serialized:
            serial_numbers = item.serial_numbers if is_grouped else (
                [item.serial_number] if item.serial_number else []
            )
            dialog = RemoveSerialNumberDialog(
                item_type_name=item.item_type,
                sub_type=item.sub_type or "",
                serial_numbers=serial_numbers,
                parent=self,
            )
            if dialog.exec():
                try:
                    selected = dialog.get_selected_serial_numbers()
                    notes = dialog.get_notes()
                    deleted_count = InventoryService.delete_items_by_serial_numbers(
                        selected, notes
                    )
                    if deleted_count > 0:
                        self._refresh_item_list()
                except Exception as e:
                    QMessageBox.warning(self, tr("message.validation_error"), str(e))
            return

        item_name = (
            f"{item.item_type} - {item.sub_type}" if item.sub_type else item.item_type
        )
        # For grouped items, use the total_quantity already present in the DTO
        target_item_id = item.item_ids[0] if is_grouped else item.id
        actual_quantity = item.total_quantity if is_grouped else item.quantity
        dialog = QuantityDialog(item_name, actual_quantity, is_add=False, parent=self)
        if dialog.exec():
            quantity = dialog.get_quantity()
            notes = dialog.get_notes()
            if target_item_id is not None:
                try:
                    updated_item = InventoryService.remove_quantity(
                        target_item_id, quantity, notes
                    )
                    if updated_item:
                        self._refresh_item_list()
                except ValueError as e:
                    QMessageBox.warning(self, tr("message.validation_error"), str(e))

    def _on_show_transactions(self, row: int, item):
        """Handle show transactions request."""
        item_name = (
            f"{item.item_type} - {item.sub_type}" if item.sub_type else item.item_type
        )
        dialog = TransactionsDialog(
            item_type_id=item.item_type_id,
            item_name=item_name,
            item_is_serialized=item.is_serialized,
            parent=self,
        )
        loc_id = self._current_location_id
        dialog.set_transactions_callback(
            lambda type_id, start, end: TransactionService.get_transactions_by_type_and_date_range(
                type_id, start, end, location_id=loc_id
            )
        )
        dialog.exec()

    def _on_transfer_item(self, row: int, item):
        """Open the transfer dialog for an inventory item."""
        dialog = TransferDialog(item, current_location_id=self._current_location_id, parent=self)
        if dialog.exec():
            self._refresh_item_list()

    def _on_show_all_transactions(self):
        """Open the all-transactions dialog filtered to current location by default."""
        dialog = AllTransactionsDialog(
            current_location_id=self._current_location_id, parent=self
        )
        dialog.exec()

    def _get_autocomplete_suggestions(self, prefix: str, field: str) -> list:
        """Get autocomplete suggestions for search."""
        return SearchService.get_autocomplete_suggestions(
            prefix, field if field else None
        )

    def _on_search(self, query: str, field: str):
        """Handle search request (scoped to current location unless checkbox is set)."""
        field_value = field if field else None
        search_all = (
            hasattr(self, "search_widget")
            and self.search_widget.is_search_all_locations()
        )
        results = SearchService.search(
            query,
            field_value,
            save_to_history=False,
            location_id=None if search_all else self._current_location_id,
        )
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
        """Refresh the item list from database (grouped by type, filtered by location)."""
        self.inventory_model.clear()
        items = InventoryService.get_all_items_grouped(location_id=self._current_location_id)
        for item in items:
            self.inventory_model.add_item(item)

    def _restore_window_state(self):
        """Restore window size and position from core.config."""
        geometry = config.get("window.geometry")
        if geometry:
            try:
                self.restoreGeometry(bytes.fromhex(geometry))
                logger.debug("Window geometry restored from core.config")
            except (ValueError, Exception):
                logger.warning("Corrupted window geometry in config, ignoring")

        if config.get("window.maximized", False):
            self.showMaximized()
            logger.debug("Window maximized from core.config")

    def closeEvent(self, event):
        """Save window state before closing."""
        config.set(
            "window.geometry", self.saveGeometry().toHex().data().decode(), save=False
        )
        config.set("window.maximized", self.isMaximized(), save=False)
        config.save()
        logger.info("Window state saved to config")
        event.accept()
