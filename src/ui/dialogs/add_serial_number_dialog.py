"""Dialog for adding a new serial number to an existing serialized ItemType."""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
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
    QVBoxLayout,
)

from core.services import LocationService
from ui.styles import apply_button_style, apply_combo_box_style, apply_input_style
from ui.translations import tr
from ui.validators import SerialNumberValidator


class AddSerialNumberDialog(QDialog):
    """Dialog for adding a new serial number to an existing serialized ItemType."""

    def __init__(
        self,
        item_type_name: str,
        sub_type: str,
        existing_serials: list[str],
        current_location_id: int = None,
        parent=None,
    ):
        """Initialize the dialog.

        Args:
            item_type_name: The item type name (displayed read-only).
            sub_type: The sub-type name (displayed read-only).
            existing_serials: List of existing serial numbers for uniqueness validation.
            current_location_id: Pre-selected location ID.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._existing_serials = existing_serials
        self._item_type_name = item_type_name
        self._sub_type = sub_type
        self._current_location_id = current_location_id
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

        # Location (mandatory)
        loc_label = QLabel(tr("location.title"))
        loc_label.setFont(label_font)
        self.location_combo = QComboBox()
        apply_combo_box_style(self.location_combo)
        for loc in LocationService.get_all_locations():
            self.location_combo.addItem(loc.name, userData=loc.id)
        if self._current_location_id is not None:
            for i in range(self.location_combo.count()):
                if self.location_combo.itemData(i) == self._current_location_id:
                    self.location_combo.setCurrentIndex(i)
                    break
        form_layout.addRow(loc_label, self.location_combo)

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

    def get_location_id(self) -> int:
        """Return the selected location ID."""
        return self.location_combo.currentData()

    def get_notes(self) -> str:
        """Return the entered notes."""
        return self.notes_edit.text().strip()
