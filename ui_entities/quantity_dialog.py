"""Dialog for adding or removing quantity with clean QLineEdit UX."""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QIntValidator
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFrame,
    QTextEdit,
    QMessageBox,
)

from logger import logger
from ui_entities.translations import tr
from validators import validate_length
from styles import Styles, apply_input_style, apply_button_style, apply_text_edit_style


class QuantityDialog(QDialog):
    """Dialog for changing item quantity with improved UX using QLineEdit."""

    def __init__(
        self,
        item_name: str,
        current_quantity: int,
        is_add: bool = True,
        parent=None,
    ):
        super().__init__(parent)
        self._item_name = item_name
        self._current_quantity = current_quantity
        self._is_add = is_add
        self._result_quantity: int = 0
        self._result_notes: str = ""
        self._setup_ui()

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

        # Current quantity info
        current_label = QLabel(f"{tr('field.quantity')}: {self._current_quantity}")
        current_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(current_label)

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
        self._update_preview()
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

    def _update_preview(self):
        """Update the preview label showing the result."""
        text = self.quantity_input.text().strip()
        
        if not text:
            self.preview_label.setText("")
            return
        
        try:
            change = int(text)
            if self._is_add:
                new_quantity = self._current_quantity + change
                self.preview_label.setText(
                    f"{self._current_quantity} + {change} = {new_quantity}"
                )
            else:
                new_quantity = self._current_quantity - change
                self.preview_label.setText(
                    f"{self._current_quantity} - {change} = {new_quantity}"
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

                if not self._is_add and quantity > self._current_quantity:
                    errors.append(
                        f"{tr('message.not_enough_quantity')}\n"
                        f"Requested: {quantity}, Available: {self._current_quantity}"
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
        self.accept()

    def get_quantity(self) -> int:
        """Return the quantity to add/remove."""
        return self._result_quantity

    def get_notes(self) -> str:
        """Return the notes for the transaction."""
        return self._result_notes
