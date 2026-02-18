"""Dialog for adding a new serial number to an existing serialized ItemType."""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from styles import apply_button_style, apply_input_style
from ui_entities.translations import tr
from validators import SerialNumberValidator


class AddSerialNumberDialog(QDialog):
    """Dialog for adding a new serial number to an existing serialized ItemType."""

    def __init__(
        self,
        item_type_name: str,
        sub_type: str,
        existing_serials: list[str],
        parent=None,
    ):
        """Initialize the dialog.

        Args:
            item_type_name: The item type name (displayed read-only).
            sub_type: The sub-type name (displayed read-only).
            existing_serials: List of existing serial numbers for uniqueness validation.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._existing_serials = existing_serials
        self._item_type_name = item_type_name
        self._sub_type = sub_type
        self._setup_ui()

    def _setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle(tr("dialog.add_serial.title"))
        self.setMinimumWidth(400)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header
        header_label = QLabel(tr("dialog.add_serial.header"))
        header_font = QFont()
        header_font.setPointSize(14)
        header_font.setBold(True)
        header_label.setFont(header_font)
        header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header_label)

        # Item type info
        type_display = self._item_type_name
        if self._sub_type:
            type_display += f" - {self._sub_type}"
        type_info_label = QLabel(type_display)
        type_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(type_info_label)

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

        # Serial Number (required)
        serial_label = QLabel(tr("label.serial_number"))
        serial_label.setFont(label_font)
        self.serial_edit = QLineEdit()
        self.serial_edit.setPlaceholderText(tr("placeholder.serial_number"))
        self.serial_edit.setValidator(SerialNumberValidator(self))
        apply_input_style(self.serial_edit)
        form_layout.addRow(serial_label, self.serial_edit)

        # Location (optional)
        location_label = QLabel("Location:")
        self.location_edit = QLineEdit()
        apply_input_style(self.location_edit)
        form_layout.addRow(location_label, self.location_edit)

        # Condition (optional)
        condition_label = QLabel("Condition:")
        self.condition_edit = QLineEdit()
        apply_input_style(self.condition_edit)
        form_layout.addRow(condition_label, self.condition_edit)

        # Notes (optional)
        notes_label = QLabel(tr("label.notes"))
        self.notes_edit = QLineEdit()
        self.notes_edit.setPlaceholderText(tr("placeholder.notes"))
        apply_input_style(self.notes_edit)
        form_layout.addRow(notes_label, self.notes_edit)

        layout.addLayout(form_layout)
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

        self.serial_edit.setFocus()

    def _on_add_clicked(self):
        """Validate and accept the dialog."""
        serial = self.serial_edit.text().strip()

        if not serial:
            QMessageBox.warning(
                self,
                tr("message.validation_error"),
                tr("error.serial.required"),
            )
            self.serial_edit.setFocus()
            return

        if serial in self._existing_serials:
            QMessageBox.warning(
                self,
                tr("message.validation_error"),
                f"Serial number '{serial}' already exists.",
            )
            self.serial_edit.setFocus()
            self.serial_edit.selectAll()
            return

        self.accept()

    def get_serial_number(self) -> str:
        """Return the entered serial number."""
        return self.serial_edit.text().strip()

    def get_location(self) -> str:
        """Return the entered location."""
        return self.location_edit.text().strip()

    def get_condition(self) -> str:
        """Return the entered condition."""
        return self.condition_edit.text().strip()

    def get_notes(self) -> str:
        """Return the entered notes."""
        return self.notes_edit.text().strip()
