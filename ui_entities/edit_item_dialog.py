"""Dialog for editing an existing inventory item."""

from typing import List, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QIntValidator
from PyQt6.QtWidgets import (
    QDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from logger import logger
from styles import Colors, apply_button_style, apply_input_style, apply_text_edit_style
from ui_entities.inventory_item import GroupedInventoryItem, InventoryItem
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

    For serialized items, shows list of serial numbers with delete option.
    For non-serialized items, allows editing quantity.
    """

    def __init__(self, item, parent=None):
        """Initialize the edit dialog.

        Args:
            item: The inventory item to edit (InventoryItem or GroupedInventoryItem).
            parent: Parent widget.
        """
        super().__init__(parent)
        self._original_item = item
        self._is_grouped = isinstance(item, GroupedInventoryItem)
        self._is_serialized = item.is_serialized
        self._result_item: Optional[InventoryItem] = None
        self._edit_notes: str = ""
        self._deleted_serial_numbers: List[str] = []
        self._serial_numbers: List[str] = []

        # Get serial numbers list
        if self._is_grouped and item.serial_numbers:
            self._serial_numbers = list(item.serial_numbers)
        elif item.serial_number:
            self._serial_numbers = [item.serial_number]

        self._setup_ui()
        self._setup_validators()
        self._populate_fields()

    def _setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle(tr("dialog.edit.title"))
        self.setMinimumWidth(450)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header with item name
        header_text = self._original_item.item_type_name
        if self._original_item.item_sub_type:
            header_text += f" - {self._original_item.item_sub_type}"
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

        # Quantity - only editable for non-serialized items
        quantity_label = QLabel(tr("label.quantity"))
        quantity_label.setFont(label_font)

        if self._is_serialized:
            # For serialized items, quantity is read-only (count of serial numbers)
            self.quantity_input = QLineEdit()
            self.quantity_input.setReadOnly(True)
            self.quantity_input.setStyleSheet(f"background-color: {Colors.get_bg_disabled()};")
            apply_input_style(self.quantity_input)
        else:
            self.quantity_input = QLineEdit()
            self.quantity_input.setPlaceholderText(tr("placeholder.quantity"))
            quantity_validator = QIntValidator(1, 999999, self)
            self.quantity_input.setValidator(quantity_validator)
            apply_input_style(self.quantity_input, large=True)

        form_layout.addRow(quantity_label, self.quantity_input)

        # Serial Number - only for non-grouped single serialized items
        if not self._is_grouped and not self._is_serialized:
            serial_label = QLabel(tr("label.serial_number"))
            self.serial_edit = QLineEdit()
            self.serial_edit.setPlaceholderText(tr("placeholder.serial_number"))
            apply_input_style(self.serial_edit)
            form_layout.addRow(serial_label, self.serial_edit)
        else:
            self.serial_edit = None

        # Item Details (optional)
        item_details_label = QLabel(tr("label.details"))
        self.item_details_edit = QTextEdit()
        self.item_details_edit.setPlaceholderText(tr("placeholder.details"))
        self.item_details_edit.setMaximumHeight(80)
        apply_text_edit_style(self.item_details_edit)
        form_layout.addRow(item_details_label, self.item_details_edit)

        layout.addLayout(form_layout)

        # Serial numbers section for serialized items
        if self._is_serialized and self._serial_numbers:
            self._add_serial_numbers_section(layout)

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

        # Set focus to type field
        self.type_edit.setFocus()

    def _add_serial_numbers_section(self, layout: QVBoxLayout):
        """Add section showing serial numbers with delete buttons."""
        serial_group = QGroupBox(tr("dialog.details.serial_numbers"))
        serial_layout = QVBoxLayout()

        # Count label
        self.serial_count_label = QLabel(
            tr("dialog.details.serial_count").format(count=len(self._serial_numbers))
        )
        count_font = QFont()
        count_font.setBold(True)
        self.serial_count_label.setFont(count_font)
        serial_layout.addWidget(self.serial_count_label)

        # List widget
        self.serial_list = QListWidget()
        self.serial_list.setMaximumHeight(150)
        self._refresh_serial_list()
        serial_layout.addWidget(self.serial_list)

        # Delete button
        delete_btn_layout = QHBoxLayout()
        delete_btn_layout.addStretch()

        self.delete_serial_btn = QPushButton(tr("button.delete_selected"))
        apply_button_style(self.delete_serial_btn, "danger")
        self.delete_serial_btn.clicked.connect(self._on_delete_serial)
        self._update_delete_button_state()
        delete_btn_layout.addWidget(self.delete_serial_btn)

        serial_layout.addLayout(delete_btn_layout)

        serial_group.setLayout(serial_layout)
        layout.addWidget(serial_group)

    def _update_delete_button_state(self):
        """Disable delete button when only 1 serial number remains."""
        if hasattr(self, 'delete_serial_btn'):
            self.delete_serial_btn.setEnabled(len(self._serial_numbers) > 1)

    def _refresh_serial_list(self):
        """Refresh the serial numbers list widget."""
        if not hasattr(self, 'serial_list'):
            return

        self.serial_list.clear()
        for sn in self._serial_numbers:
            item = QListWidgetItem(sn)
            self.serial_list.addItem(item)

        # Update count label
        if hasattr(self, 'serial_count_label'):
            self.serial_count_label.setText(
                tr("dialog.details.serial_count").format(count=len(self._serial_numbers))
            )

        # Update quantity display
        if self._is_serialized:
            self.quantity_input.setText(str(len(self._serial_numbers)))

        self._update_delete_button_state()

    def _on_delete_serial(self):
        """Handle delete serial number button click."""
        selected_items = self.serial_list.selectedItems()
        if not selected_items:
            QMessageBox.information(
                self,
                tr("dialog.edit.title"),
                tr("message.select_serial_to_delete"),
            )
            return

        # Confirm deletion
        serial_to_delete = selected_items[0].text()
        reply = QMessageBox.question(
            self,
            tr("dialog.confirm_delete.title"),
            tr("message.confirm_delete_serial").format(serial=serial_to_delete),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self._serial_numbers.remove(serial_to_delete)
            self._deleted_serial_numbers.append(serial_to_delete)
            self._refresh_serial_list()
            logger.info(f"Serial number marked for deletion: {serial_to_delete}")

    def _setup_validators(self):
        """Set up input validators for form fields."""
        self.type_edit.setValidator(ItemTypeValidator(self))
        if self.serial_edit:
            self.serial_edit.setValidator(SerialNumberValidator(self))
        logger.debug("Edit form validators configured")

    def _populate_fields(self):
        """Populate form fields with the current item values."""
        self.type_edit.setText(self._original_item.item_type_name)
        self.subtype_edit.setText(self._original_item.item_sub_type or "")

        if self._is_serialized:
            self.quantity_input.setText(str(len(self._serial_numbers)))
        else:
            self.quantity_input.setText(str(self._original_item.quantity))

        if self.serial_edit:
            self.serial_edit.setText(self._original_item.serial_number or "")

        self.item_details_edit.setPlainText(self._original_item.details or "")

    def _on_save_clicked(self):
        """Validate and accept the dialog."""
        item_type = self.type_edit.text().strip()
        sub_type = self.subtype_edit.text().strip()
        quantity_text = self.quantity_input.text().strip()
        serial_number = self.serial_edit.text().strip() if self.serial_edit else ""
        item_details = self.item_details_edit.toPlainText().strip()
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

        # Validate quantity - must not be empty (for non-serialized)
        if not self._is_serialized:
            if not quantity_text:
                errors.append(tr("message.quantity_required"))
                logger.warning("Quantity field is empty")
            else:
                try:
                    quantity_val = int(quantity_text)
                    valid, error = validate_positive_integer(
                        str(quantity_val), tr("field.quantity"), minimum=1
                    )
                    if not valid:
                        errors.append(error)
                except ValueError:
                    errors.append(tr("message.quantity_invalid"))
                    logger.warning(f"Invalid quantity value: {quantity_text}")

        # Validate serial number length if provided
        if serial_number:
            valid, error = validate_length(
                serial_number, tr("field.serial_number"), max_length=255
            )
            if not valid:
                errors.append(error)

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

        # For serialized items, check that at least one serial number remains
        if self._is_serialized and len(self._serial_numbers) == 0:
            errors.append(tr("message.at_least_one_serial"))

        # Show errors if any
        if errors:
            QMessageBox.warning(
                self,
                tr("message.validation_error"),
                tr("message.fix_errors") + "\n\n" + "\n".join(f"• {e}" for e in errors),
            )
            logger.warning(f"Edit form validation failed: {errors}")

            if not item_type:
                self.type_edit.setFocus()
            elif not self._is_serialized and (not quantity_text or not quantity_text.isdigit()):
                self.quantity_input.setFocus()
                self.quantity_input.selectAll()

            return

        # All validation passed
        # For serialized items, each item always has quantity=1
        # The "total quantity" is the count of items, not a single item's quantity
        if self._is_serialized:
            quantity = 1
        else:
            quantity = int(quantity_text)

        logger.info(
            f"Edit form validation passed - saving item with quantity {quantity}"
        )

        self._result_item = InventoryItem(
            id=self._original_item.id,
            item_type_id=self._original_item.item_type_id,
            item_type_name=item_type,
            item_sub_type=sub_type,
            is_serialized=self._original_item.is_serialized,
            quantity=quantity,
            serial_number=serial_number or None,
            location=self._original_item.location,
            condition=self._original_item.condition,
            notes=self._original_item.notes,
            details=item_details,
            created_at=self._original_item.created_at,
            updated_at=self._original_item.updated_at,
        )
        self._edit_notes = edit_reason
        self.accept()

    def get_item(self) -> Optional[InventoryItem]:
        """Return the edited item, or None if dialog was cancelled."""
        return self._result_item

    def get_original_item(self):
        """Return the original item before edits."""
        return self._original_item

    def get_edit_notes(self) -> str:
        """Return the edit reason/notes."""
        return self._edit_notes

    def get_deleted_serial_numbers(self) -> List[str]:
        """Return list of serial numbers that were deleted."""
        return self._deleted_serial_numbers
