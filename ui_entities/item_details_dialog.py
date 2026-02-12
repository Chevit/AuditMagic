from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLabel,
    QPushButton,
    QFrame,
)
from PyQt6.QtGui import QFont
from ui_entities.inventory_item import InventoryItem
from ui_entities.translations import tr
from styles import apply_button_style


class ItemDetailsDialog(QDialog):
    """Dialog for displaying inventory item details."""

    def __init__(self, item: InventoryItem, parent=None):
        super().__init__(parent)
        self._item = item
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

        # Serial Number
        serial_label = QLabel(tr("label.serial_number"))
        serial_label.setFont(label_font)
        serial_value = QLabel(
            self._item.serial_number if self._item.serial_number else "-"
        )
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

    @property
    def item(self) -> InventoryItem:
        """Return the item being displayed."""
        return self._item
