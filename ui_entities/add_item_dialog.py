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
from styles import Colors, Styles, apply_button_style, apply_input_style, apply_text_edit_style
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
        self._setup_autocomplete()
        self._setup_serialization_logic()

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

        # Serialization checkbox
        serialized_label = QLabel(tr("label.has_serial"))
        serialized_label.setFont(label_font)
        self.serialized_checkbox = QCheckBox(tr("label.has_serial_items"))
        self.serialized_checkbox.setToolTip(tr("tooltip.has_serial"))
        form_layout.addRow(serialized_label, self.serialized_checkbox)

        # Status label — shows feedback when an existing type is detected
        self.type_status_label = QLabel("")
        self.type_status_label.setStyleSheet(
            f"color: {Colors.get_text_secondary()}; font-style: italic;"
        )
        form_layout.addRow("", self.type_status_label)

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

        # Initial notes (optional) — stored as transaction notes on first ADD
        initial_notes_label = QLabel(tr("label.initial_notes"))
        self.initial_notes_edit = QTextEdit()
        self.initial_notes_edit.setPlaceholderText(tr("placeholder.initial_notes"))
        self.initial_notes_edit.setMaximumHeight(60)
        apply_text_edit_style(self.initial_notes_edit)
        form_layout.addRow(initial_notes_label, self.initial_notes_edit)

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

        # Existing-type lookup — locks serialized checkbox if type already exists
        self.type_edit.textChanged.connect(self._on_type_or_subtype_changed)
        self.subtype_edit.textChanged.connect(self._on_type_or_subtype_changed)

        logger.debug("Autocomplete configured")

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

    def _setup_serialization_logic(self):
        """Connect serialization checkbox to enable/disable logic."""
        self.serialized_checkbox.checkStateChanged.connect(self._on_serialization_changed)
        # Initialize state (unchecked by default)
        self._on_serialization_changed(self.serialized_checkbox.checkState())
        # Run initial type lookup (fields may be pre-filled)
        self._on_type_or_subtype_changed()
        logger.debug("Serialization logic configured")

    def _on_serialization_changed(self, state):
        """Handle serialization checkbox change.

        When checked:
            - Serial number field enabled
            - Quantity field disabled and set to 1
        When unchecked:
            - Serial number field disabled and cleared
            - Quantity field enabled
        """
        is_serialized = (state == Qt.CheckState.Checked)

        if is_serialized:
            # Enable serial number
            self.serial_edit.setEnabled(True)
            self.serial_edit.setStyleSheet("")
            apply_input_style(self.serial_edit)

            # Disable and fix quantity to 1
            self.quantity_input.setEnabled(False)
            self.quantity_input.setText("1")
            self.quantity_input.setStyleSheet(f"background-color: {Colors.get_bg_disabled()};")
        else:
            # Disable and clear serial number
            self.serial_edit.setEnabled(False)
            self.serial_edit.clear()
            self.serial_edit.setStyleSheet(f"background-color: {Colors.get_bg_disabled()};")

            # Enable quantity
            self.quantity_input.setEnabled(True)
            self.quantity_input.setStyleSheet("")
            apply_input_style(self.quantity_input, large=True)

    def _on_type_or_subtype_changed(self):
        """Check if the current type/subtype combination already exists in the DB.

        If it does, lock the serialized checkbox to the existing type's state
        so the user cannot submit a conflicting value.
        """
        type_name = self.type_edit.text().strip()
        sub_type = self.subtype_edit.text().strip()

        if not type_name:
            self._unlock_serialized_checkbox()
            self.type_status_label.setText("")
            return

        try:
            existing = InventoryService.get_item_type_by_name_subtype(type_name, sub_type)
        except Exception as e:
            logger.warning(f"Type lookup failed: {e}")
            return

        if existing is not None:
            self.serialized_checkbox.setChecked(existing.is_serialized)
            self.serialized_checkbox.setEnabled(False)
            self.serialized_checkbox.setToolTip(tr("tooltip.serialized_locked"))
            if existing.is_serialized:
                self.type_status_label.setText(tr("message.type_exists_serialized"))
            else:
                self.type_status_label.setText(tr("message.type_exists_non_serialized"))
            # Update dependent fields (serial/quantity) to match the locked state
            self._on_serialization_changed(self.serialized_checkbox.checkState())
        else:
            self._unlock_serialized_checkbox()
            self.type_status_label.setText("")

    def _unlock_serialized_checkbox(self):
        """Re-enable the serialized checkbox for a new (not-yet-existing) type."""
        self.serialized_checkbox.setEnabled(True)
        self.serialized_checkbox.setToolTip(tr("tooltip.has_serial"))

    def _on_add_clicked(self):
        """Validate and accept the dialog."""
        item_type = self.type_edit.text().strip()
        sub_type = self.subtype_edit.text().strip()
        quantity_text = self.quantity_input.text().strip()
        serial_number = self.serial_edit.text().strip()
        initial_notes = self.initial_notes_edit.toPlainText().strip()
        is_serialized = self.serialized_checkbox.isChecked()

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

        # Validate serial number if serialized
        if is_serialized:
            if not serial_number:
                errors.append(tr("error.serial.required"))
                logger.warning("Serial number required for serialized item")
            elif serial_number:
                valid, error = validate_length(
                    serial_number, tr("field.serial_number"), max_length=255
                )
                if not valid:
                    errors.append(error)
        else:
            # Non-serialized items shouldn't have serial numbers
            if serial_number:
                errors.append(tr("error.serial.not_allowed"))
                logger.warning("Serial number not allowed for non-serialized item")

        # Validate initial notes length if provided
        if initial_notes:
            valid, error = validate_length(
                initial_notes, tr("label.initial_notes"), max_length=1000
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
            elif is_serialized and not serial_number:
                self.serial_edit.setFocus()
            elif not quantity_text or quantity_text and not quantity_text.isdigit():
                self.quantity_input.setFocus()
                self.quantity_input.selectAll()

            return

        # All validation passed - create item via service
        quantity = int(quantity_text)
        logger.info(f"Form validation passed - creating item: type='{item_type}', qty={quantity}, serialized={is_serialized}")

        try:
            if is_serialized:
                self._result_item = InventoryService.create_serialized_item(
                    item_type_name=item_type,
                    item_sub_type=sub_type,
                    serial_number=serial_number,
                    notes=initial_notes or "",
                )
            else:
                self._result_item = InventoryService.create_item(
                    item_type_name=item_type,
                    item_sub_type=sub_type,
                    quantity=quantity,
                    is_serialized=False,
                    transaction_notes=initial_notes or None,
                )
            logger.info(f"Item created successfully: id={self._result_item.id}")
            self.accept()
        except ValueError as e:
            # Validation error from service/repository
            QMessageBox.warning(
                self,
                tr("message.validation_error"),
                str(e)
            )
            logger.error(f"Item creation failed with validation error: {e}")
        except Exception as e:
            # Unexpected error
            QMessageBox.critical(
                self,
                tr("error.generic.title"),
                f"{tr('error.generic.message')}\n\n{str(e)}"
            )
            logger.error(f"Item creation failed: {e}", exc_info=True)

    def get_item(self) -> Optional[InventoryItem]:
        """Return the created item, or None if dialog was cancelled."""
        return self._result_item
