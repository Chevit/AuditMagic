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


class AddItemDialog(QDialog):
    """Dialog for adding a new inventory item."""

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
        self.quantity_spin.setMinimum(1)
        self.quantity_spin.setMaximum(999999)
        self.quantity_spin.setValue(1)
        form_layout.addRow(quantity_label, self.quantity_spin)

        # Serial Number (optional)
        serial_label = QLabel(tr("label.serial_number"))
        self.serial_edit = QLineEdit()
        self.serial_edit.setPlaceholderText(tr("placeholder.serial_number"))
        form_layout.addRow(serial_label, self.serial_edit)

        # Details (optional)
        details_label = QLabel(tr("label.details"))
        self.details_edit = QTextEdit()
        self.details_edit.setPlaceholderText(tr("placeholder.details"))
        self.details_edit.setMaximumHeight(80)
        form_layout.addRow(details_label, self.details_edit)

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
        quantity = self.quantity_spin.value()
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

        # Validate quantity
        valid, error = validate_positive_integer(
            str(quantity), tr("field.quantity"), minimum=1
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
            return

        logger.info("Form validation passed")
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
