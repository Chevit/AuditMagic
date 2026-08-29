"""Dialog for adding or removing quantity with clean QLineEdit UX."""

from typing import List, Optional, Tuple

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QIntValidator
from PyQt6.QtWidgets import (
    QComboBox,
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

from core.logger import logger
from ui.styles import (
    apply_button_style,
    apply_combo_box_style,
    apply_input_style,
    apply_text_edit_style,
)
from ui.translations import tr
from ui.validators import validate_length


class QuantityDialog(QDialog):
    """Dialog for changing item quantity with improved UX using QLineEdit."""

    def __init__(
        self,
        item_name: str,
        current_quantity: int,
        is_add: bool = True,
        parent=None,
        locations: Optional[List[Tuple[int, str, int]]] = None,
        current_location_id: Optional[int] = None,
    ):
        """
        Args:
            item_name: Display name of the item type.
            current_quantity: Fallback available quantity when no locations given.
            is_add: True for an add dialog, False for remove.
            parent: Parent widget.
            locations: (location_id, name, available_quantity) options for the
                       location combo. Adding offers every location; removing
                       offers only those holding stock.
            current_location_id: Location to pre-select.
        """
        super().__init__(parent)
        self._item_name = item_name
        self._current_quantity = current_quantity
        self._is_add = is_add
        self._locations = locations or []
        self._current_location_id = current_location_id
        self._result_quantity: int = 0
        self._result_notes: str = ""
        self._result_location_id: Optional[int] = current_location_id
        self.location_combo: Optional[QComboBox] = None
        self._setup_ui()

    def _available(self) -> int:
        """Available quantity at the selected location."""
        if self.location_combo is None:
            return self._current_quantity
        selected = self.location_combo.currentData()
        for location_id, _name, quantity in self._locations:
            if location_id == selected:
                return quantity
        return 0

    def _setup_ui(self):
        """Set up the dialog UI."""
        title = tr("dialog.quantity.title")
        self.setWindowTitle(title)
        self.setMinimumWidth(400)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header
        header_text = (
            tr("dialog.quantity.add_header")
            if self._is_add
            else tr("dialog.quantity.remove_header")
        )
        header_label = QLabel(header_text)
        header_font = QFont()
        header_font.setPointSize(14)
        header_font.setBold(True)
        header_label.setFont(header_font)
        header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header_label)

        # Item name
        item_label = QLabel(self._item_name)
        item_font = QFont()
        item_font.setPointSize(11)
        item_label.setFont(item_font)
        item_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(item_label)

        # Current quantity info — tracks the selected location
        self.current_label = QLabel()
        self.current_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.current_label)

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

        # Location — which stock this movement applies to
        if self._locations:
            location_label = QLabel(tr("location.title"))
            location_label.setFont(label_font)
            self.location_combo = QComboBox()
            apply_combo_box_style(self.location_combo)
            for location_id, name, _quantity in self._locations:
                self.location_combo.addItem(name, userData=location_id)
            if self._current_location_id is not None:
                index = self.location_combo.findData(self._current_location_id)
                if index >= 0:
                    self.location_combo.setCurrentIndex(index)
            self.location_combo.setEnabled(len(self._locations) > 1)
            self.location_combo.currentIndexChanged.connect(self._on_location_changed)
            form_layout.addRow(location_label, self.location_combo)

        # Quantity - QLineEdit instead of QSpinBox for better UX
        quantity_label = QLabel(tr("label.quantity"))
        quantity_label.setFont(label_font)

        self.quantity_input = QLineEdit()
        self.quantity_input.setPlaceholderText("Enter quantity (e.g., 5)...")

        # Set validator to only allow positive integers
        validator = QIntValidator(1, 999999, self)
        self.quantity_input.setValidator(validator)

        # Style the input
        apply_input_style(self.quantity_input, large=True)

        # Connect text change to update preview
        self.quantity_input.textChanged.connect(self._update_preview)

        form_layout.addRow(quantity_label, self.quantity_input)

        # Notes
        notes_label = QLabel(tr("label.notes"))
        notes_label.setFont(label_font)
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText(tr("placeholder.notes"))
        self.notes_edit.setMaximumHeight(60)
        apply_text_edit_style(self.notes_edit)
        form_layout.addRow(notes_label, self.notes_edit)

        layout.addLayout(form_layout)

        # Preview
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._refresh_available()
        layout.addWidget(self.preview_label)

        # Spacer
        layout.addStretch()

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_button = QPushButton(tr("button.cancel"))
        apply_button_style(cancel_button, "danger")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        action_text = tr("button.add") if self._is_add else tr("button.delete")
        action_button = QPushButton(action_text)
        apply_button_style(action_button, "primary")
        action_button.setDefault(True)
        action_button.clicked.connect(self._on_action_clicked)
        button_layout.addWidget(action_button)

        layout.addLayout(button_layout)

        # Set focus to quantity input
        self.quantity_input.setFocus()

    def _on_location_changed(self, _index: int):
        """Re-read the available quantity when the location changes."""
        self._refresh_available()

    def _refresh_available(self):
        """Update the current-quantity label and preview for the selection."""
        self.current_label.setText(f"{tr('field.quantity')}: {self._available()}")
        self._update_preview()

    def _update_preview(self):
        """Update the preview label showing the result."""
        text = self.quantity_input.text().strip()

        if not text:
            self.preview_label.setText("")
            return

        available = self._available()
        try:
            change = int(text)
            if self._is_add:
                self.preview_label.setText(
                    f"{available} + {change} = {available + change}"
                )
            else:
                self.preview_label.setText(
                    f"{available} - {change} = {available - change}"
                )
        except ValueError:
            self.preview_label.setText("")

    def _on_action_clicked(self):
        """Handle action button click with validation."""
        text = self.quantity_input.text().strip()
        notes = self.notes_edit.toPlainText().strip()

        errors = []

        # Check if quantity field is empty
        if not text:
            errors.append("Please enter a quantity value")
            logger.warning("Quantity field is empty")
        else:
            try:
                quantity = int(text)

                if quantity < 1:
                    errors.append(tr("message.quantity_positive"))

                if not self._is_add and quantity > self._available():
                    errors.append(
                        f"{tr('message.not_enough_quantity')}\n"
                        f"Requested: {quantity}, Available: {self._available()}"
                    )

            except ValueError:
                errors.append("Quantity must be a valid number")
                logger.warning(f"Invalid quantity value: {text}")

        # Validate notes length if provided
        if notes:
            valid, error = validate_length(notes, tr("field.notes"), max_length=1000)
            if not valid:
                errors.append(error)

        if errors:
            QMessageBox.warning(
                self,
                tr("message.validation_error"),
                tr("message.fix_errors") + "\n\n" + "\n".join(f"• {e}" for e in errors),
            )
            logger.warning(f"Quantity validation failed: {errors}")
            self.quantity_input.setFocus()
            self.quantity_input.selectAll()
            return

        # All validation passed
        quantity = int(text)
        logger.info(
            f"Quantity validation passed: {'add' if self._is_add else 'remove'} {quantity}"
        )
        self._result_quantity = quantity
        self._result_notes = notes
        if self.location_combo is not None:
            self._result_location_id = self.location_combo.currentData()
        self.accept()

    def get_quantity(self) -> int:
        """Return the quantity to add/remove."""
        return self._result_quantity

    def get_notes(self) -> str:
        """Return the notes for the transaction."""
        return self._result_notes

    def get_location_id(self) -> Optional[int]:
        """Return the location this movement applies to."""
        return self._result_location_id
