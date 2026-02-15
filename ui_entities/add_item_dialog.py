from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QIntValidator
from PyQt6.QtWidgets import (
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from logger import logger
from styles import Styles, apply_button_style, apply_input_style, apply_text_edit_style
from ui_entities.inventory_item import InventoryItem
from ui_entities.translations import tr
from validators import (
    ItemTypeValidator,
    SerialNumberValidator,
    validate_length,
    validate_positive_integer,
    validate_required_field,
)


class AddItemDialog(QDialog):
    """Dialog for adding a new inventory item with improved quantity input UX."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._result_item: Optional[InventoryItem] = None
        self._setup_ui()
        self._setup_validators()

    def _setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle(tr("dialog.add_item.title"))
        self.setMinimumWidth(400)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

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
        apply_input_style(self.type_edit)
        form_layout.addRow(type_label, self.type_edit)

        # Sub-type (optional)
        subtype_label = QLabel(tr("label.subtype"))
        self.subtype_edit = QLineEdit()
        self.subtype_edit.setPlaceholderText(tr("placeholder.subtype"))
        apply_input_style(self.subtype_edit)
        form_layout.addRow(subtype_label, self.subtype_edit)

        # Quantity - QLineEdit instead of QSpinBox for better UX
        quantity_label = QLabel(tr("label.quantity"))
        quantity_label.setFont(label_font)

        self.quantity_input = QLineEdit()
        self.quantity_input.setPlaceholderText("Enter quantity (e.g., 5)...")

        # Set validator to only allow positive integers
        quantity_validator = QIntValidator(1, 999999, self)
        self.quantity_input.setValidator(quantity_validator)

        # Style the input
        apply_input_style(self.quantity_input, large=True)

        form_layout.addRow(quantity_label, self.quantity_input)

        # Serial Number (optional)
        serial_label = QLabel(tr("label.serial_number"))
        self.serial_edit = QLineEdit()
        self.serial_edit.setPlaceholderText(tr("placeholder.serial_number"))
        apply_input_style(self.serial_edit)
        form_layout.addRow(serial_label, self.serial_edit)

        # Details (optional)
        details_label = QLabel(tr("label.details"))
        self.details_edit = QTextEdit()
        self.details_edit.setPlaceholderText(tr("placeholder.details"))
        self.details_edit.setMaximumHeight(80)
        apply_text_edit_style(self.details_edit)
        form_layout.addRow(details_label, self.details_edit)

        layout.addLayout(form_layout)

        # Spacer
        layout.addStretch()

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_button = QPushButton(tr("button.cancel"))
        apply_button_style(cancel_button, "danger")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        add_button = QPushButton(tr("button.add"))
        apply_button_style(add_button, "primary")
        add_button.setDefault(True)
        add_button.clicked.connect(self._on_add_clicked)
        button_layout.addWidget(add_button)

        layout.addLayout(button_layout)

        # Set focus to type field (first field)
        self.type_edit.setFocus()

    def _setup_validators(self):
        """Set up input validators for form fields."""
        # Item type - letters, numbers, spaces, basic punctuation
        self.type_edit.setValidator(ItemTypeValidator(self))

        # Serial number - alphanumeric with hyphens
        self.serial_edit.setValidator(SerialNumberValidator(self))

        logger.debug("Form validators configured")

    def _on_add_clicked(self):
        """Validate and accept the dialog."""
        item_type = self.type_edit.text().strip()
        sub_type = self.subtype_edit.text().strip()
        quantity_text = self.quantity_input.text().strip()
        serial_number = self.serial_edit.text().strip()
        details = self.details_edit.toPlainText().strip()

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

        # Validate quantity - must not be empty
        if not quantity_text:
            errors.append("Please enter a quantity value")
            logger.warning("Quantity field is empty")
        else:
            try:
                quantity = int(quantity_text)
                valid, error = validate_positive_integer(
                    str(quantity), tr("field.quantity"), minimum=1
                )
                if not valid:
                    errors.append(error)
            except ValueError:
                errors.append("Quantity must be a valid number")
                logger.warning(f"Invalid quantity value: {quantity_text}")

        # Validate serial number length if provided
        if serial_number:
            valid, error = validate_length(
                serial_number, tr("field.serial_number"), max_length=255
            )
            if not valid:
                errors.append(error)

        # Validate details length if provided
        if details:
            valid, error = validate_length(
                details, tr("field.details"), max_length=1000
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
            logger.warning(f"Form validation failed: {errors}")

            # Focus on the first problematic field
            if not item_type:
                self.type_edit.setFocus()
            elif not quantity_text or quantity_text and not quantity_text.isdigit():
                self.quantity_input.setFocus()
                self.quantity_input.selectAll()

            return

        # All validation passed
        quantity = int(quantity_text)
        logger.info(f"Form validation passed - adding item with quantity {quantity}")
        self._result_item = InventoryItem(
            item_type=item_type,
            sub_type=sub_type,
            quantity=quantity,
            serial_number=serial_number,
            details=details,
        )
        self.accept()

    def get_item(self) -> Optional[InventoryItem]:
        """Return the created item, or None if dialog was cancelled."""
        return self._result_item
