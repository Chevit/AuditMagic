"""Dialog for adding or removing quantity from an item."""
from typing import Optional
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QSpinBox, QPushButton, QFrame, QTextEdit, QMessageBox
)
from PyQt6.QtGui import QFont
from ui_entities.translations import tr


class QuantityDialog(QDialog):
    """Dialog for changing item quantity."""

    def __init__(self, item_name: str, current_quantity: int, is_add: bool = True, parent=None):
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
        self.setMinimumWidth(350)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Header
        header_text = tr("dialog.quantity.add_header") if self._is_add else tr("dialog.quantity.remove_header")
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

        # Quantity
        quantity_label = QLabel(tr("label.quantity"))
        quantity_label.setFont(label_font)
        self.quantity_spin = QSpinBox()
        self.quantity_spin.setMinimum(1)
        self.quantity_spin.setMaximum(999999 if self._is_add else self._current_quantity)
        self.quantity_spin.setValue(1)
        form_layout.addRow(quantity_label, self.quantity_spin)

        # Notes
        notes_label = QLabel(tr("label.notes"))
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText(tr("placeholder.notes"))
        self.notes_edit.setMaximumHeight(60)
        form_layout.addRow(notes_label, self.notes_edit)

        layout.addLayout(form_layout)

        # Preview
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._update_preview()
        self.quantity_spin.valueChanged.connect(self._update_preview)
        layout.addWidget(self.preview_label)

        # Spacer
        layout.addStretch()

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_button = QPushButton(tr("button.cancel"))
        cancel_button.setMinimumWidth(100)
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        action_text = tr("button.add") if self._is_add else tr("button.delete")
        action_button = QPushButton(action_text)
        action_button.setMinimumWidth(100)
        action_button.setDefault(True)
        action_button.clicked.connect(self._on_action_clicked)
        button_layout.addWidget(action_button)

        layout.addLayout(button_layout)

    def _update_preview(self):
        """Update the preview label showing the result."""
        change = self.quantity_spin.value()
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

    def _on_action_clicked(self):
        """Handle action button click."""
        quantity = self.quantity_spin.value()

        if quantity <= 0:
            QMessageBox.warning(
                self,
                tr("message.validation_error"),
                tr("message.quantity_positive")
            )
            return

        if not self._is_add and quantity > self._current_quantity:
            QMessageBox.warning(
                self,
                tr("message.validation_error"),
                tr("message.not_enough_quantity")
            )
            return

        self._result_quantity = quantity
        self._result_notes = self.notes_edit.toPlainText().strip()
        self.accept()

    def get_quantity(self) -> int:
        """Return the quantity to add/remove."""
        return self._result_quantity

    def get_notes(self) -> str:
        """Return the notes for the transaction."""
        return self._result_notes
