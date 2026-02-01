from typing import Optional
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QSpinBox, QPushButton, QFrame, QMessageBox
)
from PyQt6.QtGui import QFont
from ui_entities.inventory_item import InventoryItem


class AddItemDialog(QDialog):
    """Dialog for adding a new inventory item."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._result_item: Optional[InventoryItem] = None
        self._setup_ui()

    def _setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle("Add New Item")
        self.setMinimumWidth(400)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Header
        header_label = QLabel("Add New Inventory Item")
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

        # Form
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        label_font = QFont()
        label_font.setBold(True)

        # Type
        type_label = QLabel("Type:")
        type_label.setFont(label_font)
        self.type_edit = QLineEdit()
        self.type_edit.setPlaceholderText("Enter item type...")
        form_layout.addRow(type_label, self.type_edit)

        # Sub-type (optional)
        subtype_label = QLabel("Sub-type:")
        self.subtype_edit = QLineEdit()
        self.subtype_edit.setPlaceholderText("Enter item sub-type (optional)...")
        form_layout.addRow(subtype_label, self.subtype_edit)

        # Quantity
        quantity_label = QLabel("Quantity:")
        quantity_label.setFont(label_font)
        self.quantity_spin = QSpinBox()
        self.quantity_spin.setMinimum(0)
        self.quantity_spin.setMaximum(999999)
        self.quantity_spin.setValue(1)
        form_layout.addRow(quantity_label, self.quantity_spin)

        # Serial Number (optional)
        serial_label = QLabel("Serial Number:")
        self.serial_edit = QLineEdit()
        self.serial_edit.setPlaceholderText("Enter serial number (optional)...")
        form_layout.addRow(serial_label, self.serial_edit)

        layout.addLayout(form_layout)

        # Spacer
        layout.addStretch()

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_button = QPushButton("Cancel")
        cancel_button.setMinimumWidth(100)
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        add_button = QPushButton("Add")
        add_button.setMinimumWidth(100)
        add_button.setDefault(True)
        add_button.clicked.connect(self._on_add_clicked)
        button_layout.addWidget(add_button)

        layout.addLayout(button_layout)

    def _on_add_clicked(self):
        """Validate and accept the dialog."""
        item_type = self.type_edit.text().strip()
        sub_type = self.subtype_edit.text().strip()
        quantity = self.quantity_spin.value()
        serial_number = self.serial_edit.text().strip()

        # Validation - only Type is required
        errors = []
        if not item_type:
            errors.append("Type is required")

        if errors:
            QMessageBox.warning(
                self,
                "Validation Error",
                "Please fix the following errors:\n\n" + "\n".join(f"• {e}" for e in errors)
            )
            return

        self._result_item = InventoryItem(
            item_type=item_type,
            sub_type=sub_type,
            quantity=quantity,
            serial_number=serial_number
        )
        self.accept()

    def get_item(self) -> Optional[InventoryItem]:
        """Return the created item, or None if dialog was cancelled."""
        return self._result_item
