"""Dialog for editing an existing inventory item."""

from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QPushButton,
    QFrame,
    QMessageBox,
    QTextEdit,
)

from logger import logger
from ui_entities.inventory_item import InventoryItem
from ui_entities.translations import tr
from validators import (
    ItemTypeValidator,
    SerialNumberValidator,
    validate_required_field,
    validate_positive_integer,
    validate_length,
)


class EditItemDialog(QDialog):
    """Dialog for editing an existing inventory item.

    All fields are pre-filled with the current item values.
    The notes field (reason for edit) is required.
    """

    def __init__(self, item: InventoryItem, parent=None):
        """Initialize the edit dialog.

        Args:
            item: The inventory item to edit.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._original_item = item
        self._result_item: Optional[InventoryItem] = None
        self._edit_notes: str = ""
        self._setup_ui()
        self._setup_validators()
        self._populate_fields()

    def _setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle(tr("dialog.edit.title"))
        self.setMinimumWidth(400)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Header
        header_label = QLabel(tr("dialog.edit.header"))
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
        form_layout.addRow(quantity_label, self.quantity_spin)

        # Serial Number (optional)
        serial_label = QLabel(tr("label.serial_number"))
        self.serial_edit = QLineEdit()
        self.serial_edit.setPlaceholderText(tr("placeholder.serial_number"))
        form_layout.addRow(serial_label, self.serial_edit)

        # Item Notes (optional)
        item_notes_label = QLabel(tr("label.notes"))
        self.item_notes_edit = QTextEdit()
        self.item_notes_edit.setPlaceholderText(tr("placeholder.notes"))
        self.item_notes_edit.setMaximumHeight(60)
        form_layout.addRow(item_notes_label, self.item_notes_edit)

        layout.addLayout(form_layout)

        # Separator before edit reason
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.Shape.HLine)
        separator2.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator2)

        # Edit reason (required)
        reason_layout = QFormLayout()
        reason_layout.setSpacing(10)
        reason_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        reason_label = QLabel(tr("label.edit_reason"))
        reason_label.setFont(label_font)
        self.reason_edit = QTextEdit()
        self.reason_edit.setPlaceholderText(tr("placeholder.edit_reason"))
        self.reason_edit.setMaximumHeight(60)
        reason_layout.addRow(reason_label, self.reason_edit)

        layout.addLayout(reason_layout)

        # Spacer
        layout.addStretch()

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_button = QPushButton(tr("button.cancel"))
        cancel_button.setMinimumWidth(100)
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        save_button = QPushButton(tr("button.save"))
        save_button.setMinimumWidth(100)
        save_button.setDefault(True)
        save_button.clicked.connect(self._on_save_clicked)
        button_layout.addWidget(save_button)

        layout.addLayout(button_layout)

    def _setup_validators(self):
        """Set up input validators for form fields."""
        self.type_edit.setValidator(ItemTypeValidator(self))
        self.serial_edit.setValidator(SerialNumberValidator(self))
        logger.debug("Edit form validators configured")

    def _populate_fields(self):
        """Populate form fields with the current item values."""
        self.type_edit.setText(self._original_item.item_type)
        self.subtype_edit.setText(self._original_item.sub_type or "")
        self.quantity_spin.setValue(self._original_item.quantity)
        self.serial_edit.setText(self._original_item.serial_number or "")
        self.item_notes_edit.setPlainText(self._original_item.notes or "")

    def _on_save_clicked(self):
        """Validate and accept the dialog."""
        item_type = self.type_edit.text().strip()
        sub_type = self.subtype_edit.text().strip()
        quantity = self.quantity_spin.value()
        serial_number = self.serial_edit.text().strip()
        item_notes = self.item_notes_edit.toPlainText().strip()
        edit_reason = self.reason_edit.toPlainText().strip()

        # Validation
        errors = []

        # Validate item type - required and min length
        valid, error = validate_required_field(item_type, tr("field.type"))
        if not valid:
            errors.append(error)
        else:
            valid, error = validate_length(
                item_type, tr("field.type"), min_length=2, max_length=255
            )
            if not valid:
                errors.append(error)

        # Validate quantity
        valid, error = validate_positive_integer(
            str(quantity), tr("field.quantity"), minimum=0
        )
        if not valid:
            errors.append(error)

        # Validate serial number length if provided
        if serial_number:
            valid, error = validate_length(
                serial_number, tr("field.serial_number"), max_length=255
            )
            if not valid:
                errors.append(error)

        # Validate item notes length if provided
        if item_notes:
            valid, error = validate_length(
                item_notes, tr("field.notes"), max_length=1000
            )
            if not valid:
                errors.append(error)

        # Validate edit reason - required
        valid, error = validate_required_field(edit_reason, tr("field.edit_reason"))
        if not valid:
            errors.append(error)
        else:
            valid, error = validate_length(
                edit_reason, tr("field.edit_reason"), min_length=3, max_length=1000
            )
            if not valid:
                errors.append(error)

        # Show errors if any
        if errors:
            QMessageBox.warning(
                self,
                tr("message.validation_error"),
                tr("message.fix_errors") + "\n\n" + "\n".join(f"• {e}" for e in errors),
            )
            logger.warning(f"Edit form validation failed: {errors}")
            return

        logger.info("Edit form validation passed")
        self._result_item = InventoryItem(
            id=self._original_item.id,
            item_type=item_type,
            sub_type=sub_type,
            quantity=quantity,
            serial_number=serial_number,
            notes=item_notes,
        )
        self._edit_notes = edit_reason
        self.accept()

    def get_item(self) -> Optional[InventoryItem]:
        """Return the edited item, or None if dialog was cancelled."""
        return self._result_item

    def get_original_item(self) -> InventoryItem:
        """Return the original item before edits."""
        return self._original_item

    def get_edit_notes(self) -> str:
        """Return the edit reason/notes."""
        return self._edit_notes
