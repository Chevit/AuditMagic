"""Dialog for editing an existing inventory item."""

from typing import Optional

from PyQt6.QtCore import Qt, QStringListModel
from PyQt6.QtGui import QFont, QIntValidator
from PyQt6.QtWidgets import (
    QCheckBox,
    QCompleter,
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
from services import InventoryService
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
        self._setup_autocomplete()
        self._populate_fields()
        self._setup_serialization_constraints()

    def _setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle(tr("dialog.edit.title"))
        self.setMinimumWidth(400)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

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

        # Type (read-only for serialized items)
        type_label = QLabel(tr("label.type"))
        type_label.setFont(label_font)
        self.type_edit = QLineEdit()
        self.type_edit.setPlaceholderText(tr("placeholder.type"))
        apply_input_style(self.type_edit)
        form_layout.addRow(type_label, self.type_edit)

        # Sub-type (read-only for serialized items)
        subtype_label = QLabel(tr("label.subtype"))
        self.subtype_edit = QLineEdit()
        self.subtype_edit.setPlaceholderText(tr("placeholder.subtype"))
        apply_input_style(self.subtype_edit)
        form_layout.addRow(subtype_label, self.subtype_edit)

        # Serialized status indicator (read-only)
        self.serialized_label = QLabel(tr("label.is_serialized"))
        self.serialized_status = QLabel()
        self.serialized_status.setStyleSheet("color: #666666; font-style: italic;")
        form_layout.addRow(self.serialized_label, self.serialized_status)

        # Quantity - QLineEdit instead of QSpinBox for better UX
        quantity_label = QLabel(tr("label.quantity"))
        quantity_label.setFont(label_font)

        self.quantity_input = QLineEdit()
        self.quantity_input.setPlaceholderText("Enter quantity (e.g., 5)...")

        # Set validator to only allow positive integers
        quantity_validator = QIntValidator(0, 999999, self)
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

        # Item Details (optional)
        item_details_label = QLabel(tr("label.details"))
        self.item_details_edit = QTextEdit()
        self.item_details_edit.setPlaceholderText(tr("placeholder.details"))
        self.item_details_edit.setMaximumHeight(80)
        apply_text_edit_style(self.item_details_edit)
        form_layout.addRow(item_details_label, self.item_details_edit)

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
        self.reason_edit.setMaximumHeight(80)
        apply_text_edit_style(self.reason_edit)
        reason_layout.addRow(reason_label, self.reason_edit)

        layout.addLayout(reason_layout)

        # Spacer
        layout.addStretch()

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_button = QPushButton(tr("button.cancel"))
        apply_button_style(cancel_button, "danger")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        save_button = QPushButton(tr("button.save"))
        apply_button_style(save_button, "primary")
        save_button.setDefault(True)
        save_button.clicked.connect(self._on_save_clicked)
        button_layout.addWidget(save_button)

        layout.addLayout(button_layout)

        # Set focus to type field (first field)
        self.type_edit.setFocus()

    def _setup_validators(self):
        """Set up input validators for form fields."""
        self.type_edit.setValidator(ItemTypeValidator(self))
        self.serial_edit.setValidator(SerialNumberValidator(self))
        logger.debug("Edit form validators configured")

    def _setup_autocomplete(self):
        """Setup autocomplete for type and subtype fields."""
        # Type autocomplete
        self.type_completer = QCompleter(self)
        self.type_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.type_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.type_edit.setCompleter(self.type_completer)

        # Subtype autocomplete
        self.subtype_completer = QCompleter(self)
        self.subtype_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.subtype_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.subtype_edit.setCompleter(self.subtype_completer)

        # Update autocomplete on text change
        self.type_edit.textChanged.connect(self._update_type_autocomplete)
        self.type_edit.textChanged.connect(self._update_subtype_autocomplete)
        logger.debug("Autocomplete configured for edit dialog")

    def _update_type_autocomplete(self, text: str):
        """Update autocomplete suggestions for type."""
        try:
            suggestions = InventoryService.get_autocomplete_types(text)
            model = QStringListModel(suggestions)
            self.type_completer.setModel(model)
        except Exception as e:
            logger.error(f"Failed to load type autocomplete: {e}")

    def _update_subtype_autocomplete(self, type_text: str):
        """Update autocomplete suggestions for subtype based on selected type."""
        if not type_text:
            return
        try:
            suggestions = InventoryService.get_autocomplete_subtypes(type_text)
            model = QStringListModel(suggestions)
            self.subtype_completer.setModel(model)
        except Exception as e:
            logger.error(f"Failed to load subtype autocomplete: {e}")

    def _setup_serialization_constraints(self):
        """Setup UI constraints based on item's serialization status.

        For serialized items:
        - Type/SubType fields are READ-ONLY (can't change type of serialized item)
        - Quantity is locked to 1
        - Serial number is required

        For non-serialized items:
        - Type/SubType can be edited (with autocomplete)
        - Quantity can be changed
        - Serial number field is disabled
        """
        is_serialized = self._original_item.is_serialized

        if is_serialized:
            # Serialized item - type/subtype are read-only
            self.type_edit.setReadOnly(True)
            self.subtype_edit.setReadOnly(True)
            self.type_edit.setStyleSheet("background-color: #f0f0f0; color: #666666;")
            self.subtype_edit.setStyleSheet("background-color: #f0f0f0; color: #666666;")

            # Quantity locked to 1
            self.quantity_input.setReadOnly(True)
            self.quantity_input.setStyleSheet("background-color: #f0f0f0; color: #666666;")

            # Serial number enabled and required
            self.serial_edit.setEnabled(True)
            apply_input_style(self.serial_edit)

            # Update status label
            self.serialized_status.setText(tr("label.serialized_item_note"))
        else:
            # Non-serialized item - can edit type/subtype
            self.type_edit.setReadOnly(False)
            self.subtype_edit.setReadOnly(False)
            apply_input_style(self.type_edit)
            apply_input_style(self.subtype_edit)

            # Quantity editable
            self.quantity_input.setReadOnly(False)
            apply_input_style(self.quantity_input, large=True)

            # Serial number disabled
            self.serial_edit.setEnabled(False)
            self.serial_edit.setStyleSheet("background-color: #e0e0e0;")

            # Update status label
            self.serialized_status.setText(tr("label.non_serialized_item_note"))

        logger.debug(f"Serialization constraints applied: is_serialized={is_serialized}")

    def _populate_fields(self):
        """Populate form fields with the current item values."""
        self.type_edit.setText(self._original_item.item_type_name)
        self.subtype_edit.setText(self._original_item.item_sub_type or "")
        self.quantity_input.setText(str(self._original_item.quantity))
        self.serial_edit.setText(self._original_item.serial_number or "")
        self.item_details_edit.setPlainText(self._original_item.details or "")
        logger.debug(f"Populated edit form with item data: id={self._original_item.id}")

    def _on_save_clicked(self):
        """Validate and accept the dialog."""
        item_type = self.type_edit.text().strip()
        sub_type = self.subtype_edit.text().strip()
        quantity_text = self.quantity_input.text().strip()
        serial_number = self.serial_edit.text().strip()
        item_details = self.item_details_edit.toPlainText().strip()
        edit_reason = self.reason_edit.toPlainText().strip()
        is_serialized = self._original_item.is_serialized

        # Validation
        errors = []

        # Validate item type - required and min length (if editable)
        if not self.type_edit.isReadOnly():
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
                quantity_val = int(quantity_text)

                # For serialized items, quantity must be 1
                if is_serialized and quantity_val != 1:
                    errors.append(tr("error.quantity.must_be_one"))
                    logger.warning(f"Serialized item must have quantity=1, got {quantity_val}")
                else:
                    valid, error = validate_positive_integer(
                        str(quantity_val), tr("field.quantity"), minimum=1 if not is_serialized else 1
                    )
                    if not valid:
                        errors.append(error)
            except ValueError:
                errors.append("Quantity must be a valid number")
                logger.warning(f"Invalid quantity value: {quantity_text}")

        # Validate serial number based on serialization status
        if is_serialized:
            # Serialized items MUST have serial number
            if not serial_number:
                errors.append(tr("error.serial.required"))
                logger.warning("Serial number required for serialized item")
            else:
                valid, error = validate_length(
                    serial_number, tr("field.serial_number"), max_length=255
                )
                if not valid:
                    errors.append(error)
        else:
            # Non-serialized items should NOT have serial number
            if serial_number:
                errors.append(tr("error.serial.not_allowed"))
                logger.warning("Serial number not allowed for non-serialized item")

        # Validate item details length if provided
        if item_details:
            valid, error = validate_length(
                item_details, tr("field.details"), max_length=1000
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

            # Focus on the first problematic field
            if not item_type and not self.type_edit.isReadOnly():
                self.type_edit.setFocus()
            elif not quantity_text or (quantity_text and not quantity_text.isdigit()):
                self.quantity_input.setFocus()
                self.quantity_input.selectAll()
            elif is_serialized and not serial_number:
                self.serial_edit.setFocus()

            return

        # All validation passed
        quantity = int(quantity_text)
        logger.info(
            f"Edit form validation passed - saving item id={self._original_item.id} with quantity={quantity}"
        )

        # Store the edited values for retrieval
        self._edited_type = item_type
        self._edited_subtype = sub_type
        self._edited_quantity = quantity
        self._edited_serial_number = serial_number
        self._edited_details = item_details
        self._edit_notes = edit_reason

        self.accept()

    def get_item(self) -> Optional[InventoryItem]:
        """Return the edited item, or None if dialog was cancelled.

        DEPRECATED: Use get_edited_values() instead for hierarchical model.
        """
        return self._result_item

    def get_original_item(self) -> InventoryItem:
        """Return the original item before edits."""
        return self._original_item

    def get_edit_notes(self) -> str:
        """Return the edit reason/notes."""
        return self._edit_notes

    def get_edited_values(self) -> dict:
        """Return the edited values as a dictionary.

        Returns:
            Dictionary with keys: type_name, sub_type, quantity, serial_number, details, edit_reason
        """
        if not hasattr(self, '_edited_type'):
            return None

        return {
            'type_name': self._edited_type,
            'sub_type': self._edited_subtype,
            'quantity': self._edited_quantity,
            'serial_number': self._edited_serial_number,
            'details': self._edited_details,
            'edit_reason': self._edit_notes
        }
