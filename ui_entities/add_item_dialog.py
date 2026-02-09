from typing import Optional
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QSpinBox, QPushButton, QFrame, QMessageBox, QTextEdit
)
from PyQt6.QtGui import QFont
from ui_entities.inventory_item import InventoryItem
from ui_entities.translations import tr


class AddItemDialog(QDialog):
    """Dialog for adding a new inventory item."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._result_item: Optional[InventoryItem] = None
        self._setup_ui()

    def _setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle(tr("dialog.add_item.title"))
        self.setMinimumWidth(400)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Header
        header_label = QLabel(tr("dialog.add_item.header"))
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
        type_label = QLabel(tr("label.type"))
        type_label.setFont(label_font)
        self.type_edit = QLineEdit()
        self.type_edit.setPlaceholderText(tr("placeholder.type"))
        form_layout.addRow(type_label, self.type_edit)

        # Sub-type (optional)
        subtype_label = QLabel(tr("label.subtype"))
        self.subtype_edit = QLineEdit()
        self.subtype_edit.setPlaceholderText(tr("placeholder.subtype"))
        form_layout.addRow(subtype_label, self.subtype_edit)

        # Quantity
        quantity_label = QLabel(tr("label.quantity"))
        quantity_label.setFont(label_font)
        self.quantity_spin = QSpinBox()
        self.quantity_spin.setMinimum(0)
        self.quantity_spin.setMaximum(999999)
        self.quantity_spin.setValue(1)
        form_layout.addRow(quantity_label, self.quantity_spin)

        # Serial Number (optional)
        serial_label = QLabel(tr("label.serial_number"))
        self.serial_edit = QLineEdit()
        self.serial_edit.setPlaceholderText(tr("placeholder.serial_number"))
        form_layout.addRow(serial_label, self.serial_edit)

        # Notes (optional)
        notes_label = QLabel(tr("label.notes"))
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText(tr("placeholder.notes"))
        self.notes_edit.setMaximumHeight(80)
        form_layout.addRow(notes_label, self.notes_edit)

        layout.addLayout(form_layout)

        # Spacer
        layout.addStretch()

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_button = QPushButton(tr("button.cancel"))
        cancel_button.setMinimumWidth(100)
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        add_button = QPushButton(tr("button.add"))
        add_button.setMinimumWidth(100)
        add_button.setDefault(True)
        add_button.clicked.connect(self._on_add_clicked)
        button_layout.addWidget(add_button)

        layout.addLayout(button_layout)

    def _on_add_clicked(self):
        item_type = self.type_edit.text().strip()
        """Validate and accept the dialog."""
        sub_type = self.subtype_edit.text().strip()
        quantity = self.quantity_spin.value()
        serial_number = self.serial_edit.text().strip()
        notes = self.notes_edit.toPlainText().strip()

        # Validation - only Type is required
        errors = []
        if not item_type:
            errors.append(tr("message.type_required"))

        if quantity <= 0:
            errors.append(tr("message.quantity_positive"))

        if errors:
            QMessageBox.warning(
                self,
                tr("message.validation_error"),
                tr("message.fix_errors") + "\n\n" + "\n".join(f"• {e}" for e in errors)
            )
            return

        self._result_item = InventoryItem(
            item_type=item_type,
            sub_type=sub_type,
            quantity=quantity,
            serial_number=serial_number,
            notes=notes
        )
        self.accept()

    def get_item(self) -> Optional[InventoryItem]:
        """Return the created item, or None if dialog was cancelled."""
        return self._result_item
