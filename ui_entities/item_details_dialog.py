from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
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

from logger import logger
from repositories import ItemRepository
from styles import apply_button_style
from ui_entities.inventory_item import GroupedInventoryItem, InventoryItem
from ui_entities.translations import tr


class ItemDetailsDialog(QDialog):
    """Dialog for displaying inventory item details."""

    def __init__(self, item, parent=None):
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

        # ID
        if self._item.id is not None:
            id_label = QLabel(tr("label.id"))
            id_label.setFont(label_font)
            id_value = QLabel(str(self._item.id))
            id_value.setFont(value_font)
            form_layout.addRow(id_label, id_value)

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

        # Quantity
        quantity_label = QLabel(tr("label.quantity"))
        quantity_label.setFont(label_font)
        quantity_value = QLabel(str(self._item.quantity))
        quantity_value.setFont(value_font)
        form_layout.addRow(quantity_label, quantity_value)

        # Serial Number (for non-grouped) or count (for grouped)
        serial_label = QLabel(tr("label.serial_number"))
        serial_label.setFont(label_font)
        if self._is_grouped:
            serial_count = len(self._item.serial_numbers) if self._item.serial_numbers else 0
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

        # Serial numbers section for serialized types (grouped items have the list directly)
        if self._is_grouped and self._item.serial_numbers:
            self._add_serial_numbers_section_from_list(layout, self._item.serial_numbers)
        elif self._item.is_serialized and not self._is_grouped:
            self._add_serial_numbers_section(layout)

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
            serial_numbers = ItemRepository.get_serial_numbers_for_type(self._item.item_type_id)
            if serial_numbers:
                self._add_serial_numbers_section_from_list(layout, serial_numbers)
        except Exception as e:
            logger.error(f"Failed to load serial numbers: {e}", exc_info=True)

    def _add_serial_numbers_section_from_list(self, layout: QVBoxLayout, serial_numbers: list):
        """Add section showing serial numbers from a provided list.

        Args:
            layout: The main layout to add to
            serial_numbers: List of serial number strings
        """
        if not serial_numbers:
            return

        # Create group box
        serial_group = QGroupBox(tr("dialog.details.serial_numbers"))
        serial_layout = QVBoxLayout()

        # Count label
        count_label = QLabel(tr("dialog.details.serial_count").format(count=len(serial_numbers)))
        count_font = QFont()
        count_font.setBold(True)
        count_label.setFont(count_font)
        serial_layout.addWidget(count_label)

        # List widget
        serial_list = QListWidget()
        serial_list.setMaximumHeight(150)
        for sn in serial_numbers:
            serial_list.addItem(sn)
        serial_layout.addWidget(serial_list)

        serial_group.setLayout(serial_layout)
        layout.addWidget(serial_group)

        logger.debug(f"Added serial numbers section with {len(serial_numbers)} items")

    @property
    def item(self) -> InventoryItem:
        """Return the item being displayed."""
        return self._item
