from typing import Dict, List, Optional, Tuple, Union

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QVBoxLayout,
)

from core.logger import logger
from core.repositories import ItemRepository
from ui.models.inventory_item import GroupedInventoryItem, InventoryItem
from ui.styles import apply_button_style
from ui.translations import tr


class ItemDetailsDialog(QDialog):
    """Dialog for displaying inventory item details."""

    def __init__(self, item: Union[InventoryItem, GroupedInventoryItem], parent=None):
        super().__init__(parent)
        self._item = item
        self._is_grouped = isinstance(item, GroupedInventoryItem)
        self._setup_ui()

    def _setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle(tr("dialog.details.title"))
        self.setMinimumWidth(400)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Header
        header_text = self._item.item_type
        if self._item.sub_type:
            header_text += f" - {self._item.sub_type}"
        header_label = QLabel(header_text)
        header_font = QFont()
        header_font.setPointSize(14)
        header_font.setBold(True)
        header_label.setFont(header_font)
        header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header_label)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)

        # Details form
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        label_font = QFont()
        label_font.setBold(True)

        value_font = QFont()
        value_font.setPointSize(10)

        # Type
        type_label = QLabel(tr("label.type"))
        type_label.setFont(label_font)
        type_value = QLabel(self._item.item_type)
        type_value.setFont(value_font)
        form_layout.addRow(type_label, type_value)

        # Sub-type
        subtype_label = QLabel(tr("label.subtype"))
        subtype_label.setFont(label_font)
        subtype_value = QLabel(self._item.sub_type if self._item.sub_type else "-")
        subtype_value.setFont(value_font)
        form_layout.addRow(subtype_label, subtype_value)

        # Serialized badge
        serialized_label = QLabel(tr("label.is_serialized"))
        serialized_label.setFont(label_font)
        is_ser = self._item.is_serialized
        badge_text = (
            tr("label.serialized_badge") if is_ser else tr("label.non_serialized_badge")
        )
        badge_color = "#2e7d32" if is_ser else "#757575"
        serialized_value = QLabel(badge_text)
        serialized_value.setFont(value_font)
        serialized_value.setStyleSheet(
            f"color: {badge_color}; font-weight: bold; padding: 2px 6px; "
            f"border: 1px solid {badge_color}; border-radius: 3px;"
        )
        form_layout.addRow(serialized_label, serialized_value)

        # Location
        location_label = QLabel(tr("label.location"))
        location_label.setFont(label_font)
        if self._item.is_multi_location:
            location_text = tr("location.multiple")
        else:
            location_text = (
                self._item.location_name if self._item.location_name else "-"
            )
        location_value = QLabel(location_text)
        location_value.setFont(value_font)
        form_layout.addRow(location_label, location_value)

        # Quantity
        quantity_label = QLabel(tr("label.quantity"))
        quantity_label.setFont(label_font)
        quantity_value = QLabel(str(self._item.quantity))
        quantity_value.setFont(value_font)
        form_layout.addRow(quantity_label, quantity_value)

        # Serial Number (for non-grouped) or count (for grouped)
        serial_label = QLabel(tr("label.serial_number"))
        serial_label.setFont(label_font)
        if isinstance(self._item, GroupedInventoryItem):
            serial_count = (
                len(self._item.serial_numbers) if self._item.serial_numbers else 0
            )
            serial_text = f"{serial_count} шт." if serial_count > 0 else "-"
        else:
            serial_text = self._item.serial_number if self._item.serial_number else "-"
        serial_value = QLabel(serial_text)
        serial_value.setFont(value_font)
        form_layout.addRow(serial_label, serial_value)

        # Details
        details_label = QLabel(tr("label.details"))
        details_label.setFont(label_font)
        details_value = QLabel(self._item.details if self._item.details else "-")
        details_value.setFont(value_font)
        details_value.setWordWrap(True)
        form_layout.addRow(details_label, details_value)

        layout.addLayout(form_layout)

        # Serial numbers section for serialized types (grouped items have list directly)
        if isinstance(self._item, GroupedInventoryItem) and self._item.serial_numbers:
            self._add_serial_numbers_section_from_list(
                layout, self._item.serial_numbers, self._item.serial_locations
            )
        elif self._item.is_serialized and not self._is_grouped:
            self._add_serial_numbers_section(layout)

        # Location breakdown for non-serialized groups spanning multiple locations
        if (
            isinstance(self._item, GroupedInventoryItem)
            and not self._item.is_serialized
            and self._item.location_breakdown
        ):
            self._add_location_breakdown_section(layout, self._item.location_breakdown)

        # Spacer
        layout.addStretch()

        # Close button
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        close_button = QPushButton(tr("button.close"))
        apply_button_style(close_button, "info")
        close_button.clicked.connect(self.accept)
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)

    def _add_serial_numbers_section(self, layout: QVBoxLayout):
        """Add section showing all serial numbers for this type (loads from DB).

        Args:
            layout: The main layout to add to
        """
        try:
            # Get all serial numbers for this type
            serial_numbers = ItemRepository.get_serial_numbers_for_type(
                self._item.item_type_id
            )
            if serial_numbers:
                self._add_serial_numbers_section_from_list(layout, serial_numbers)
        except Exception as e:
            logger.error(f"Failed to load serial numbers: {e}", exc_info=True)

    def _add_serial_numbers_section_from_list(
        self,
        layout: QVBoxLayout,
        serial_numbers: List[str],
        serial_locations: Optional[Dict[str, str]] = None,
    ):
        """Add section showing serial numbers from a provided list.

        Args:
            layout: The main layout to add to
            serial_numbers: List of serial number strings
            serial_locations: Optional {serial_number: location_name} map. When
                given (multi-location groups only), each row is annotated with
                its location and rows are ordered by location name, then serial.
        """
        if not serial_numbers:
            return

        display_serials = serial_numbers
        if serial_locations:
            display_serials = sorted(
                serial_numbers, key=lambda sn: (serial_locations.get(sn, ""), sn)
            )

        # Create group box
        serial_group = QGroupBox(tr("dialog.details.serial_numbers"))
        serial_layout = QVBoxLayout()

        # Count label
        count_label = QLabel(
            tr("dialog.details.serial_count").format(count=len(display_serials))
        )
        count_font = QFont()
        count_font.setBold(True)
        count_label.setFont(count_font)
        serial_layout.addWidget(count_label)

        # List widget
        serial_list = QListWidget()
        serial_list.setMaximumHeight(150)
        serial_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        serial_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        for sn in display_serials:
            loc_name = (serial_locations or {}).get(sn)
            item_text = f"{sn} — {loc_name}" if loc_name else sn
            serial_list.addItem(item_text)
        serial_layout.addWidget(serial_list)

        serial_group.setLayout(serial_layout)
        layout.addWidget(serial_group)

        logger.debug(f"Added serial numbers section with {len(display_serials)} items")

    def _add_location_breakdown_section(
        self, layout: QVBoxLayout, location_breakdown: List[Tuple[str, int]]
    ):
        """Add section showing per-location quantities for a multi-location group.

        Args:
            layout: The main layout to add to
            location_breakdown: [(location_name, quantity), ...], already sorted
                alphabetically by location name
        """
        if not location_breakdown:
            return

        location_group = QGroupBox(tr("location.title"))
        location_layout = QVBoxLayout()

        count_label = QLabel(
            tr("dialog.details.location_count").format(count=len(location_breakdown))
        )
        count_font = QFont()
        count_font.setBold(True)
        count_label.setFont(count_font)
        location_layout.addWidget(count_label)

        location_list = QListWidget()
        location_list.setMaximumHeight(150)
        location_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        location_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        for loc_name, qty in location_breakdown:
            location_list.addItem(f"{loc_name} — {qty} шт.")
        location_layout.addWidget(location_list)

        location_group.setLayout(location_layout)
        layout.addWidget(location_group)

        logger.debug(
            f"Added location breakdown section with {len(location_breakdown)} locations"
        )

    @property
    def item(self) -> Union[InventoryItem, GroupedInventoryItem]:
        """Return the item being displayed."""
        return self._item
