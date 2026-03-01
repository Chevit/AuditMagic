"""Dialog for selecting serial numbers to remove from a grouped serialized item."""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from styles import apply_button_style, apply_input_style
from ui_entities.translations import tr


class RemoveSerialNumberDialog(QDialog):
    """Dialog for selecting serial numbers to delete from a serialized item group."""

    def __init__(
        self,
        item_type_name: str,
        sub_type: str,
        serial_numbers: list[str],
        parent=None,
    ):
        """Initialize the dialog.

        Args:
            item_type_name: The item type name.
            sub_type: The sub-type name.
            serial_numbers: All serial numbers in the group.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._item_type_name = item_type_name
        self._sub_type = sub_type
        self._serial_numbers = serial_numbers
        self._checkboxes: list[QCheckBox] = []
        self._setup_ui()

    def _setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle(tr("dialog.remove_serial.title"))
        self.setMinimumWidth(400)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header
        header_label = QLabel(tr("dialog.remove_serial.header"))
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

        # Scrollable checkbox list
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMaximumHeight(250)

        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(5)

        for sn in self._serial_numbers:
            cb = QCheckBox(sn)
            cb.stateChanged.connect(self._update_selection_count)
            self._checkboxes.append(cb)
            scroll_layout.addWidget(cb)

        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_widget)
        layout.addWidget(scroll_area)

        # Notes/reason (required)
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        notes_label = QLabel(tr("label.notes_reason") + ":")
        notes_label_font = QFont()
        notes_label_font.setBold(True)
        notes_label.setFont(notes_label_font)
        self.notes_edit = QLineEdit()
        self.notes_edit.setPlaceholderText(tr("placeholder.edit_reason"))
        apply_input_style(self.notes_edit)
        form_layout.addRow(notes_label, self.notes_edit)
        layout.addLayout(form_layout)

        # Selection count label
        self._count_label = QLabel(f"Selected: 0 of {len(self._serial_numbers)}")
        layout.addWidget(self._count_label)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_button = QPushButton(tr("button.cancel"))
        apply_button_style(cancel_button, "secondary")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        delete_button = QPushButton(tr("button.delete"))
        apply_button_style(delete_button, "danger")
        delete_button.setDefault(True)
        delete_button.clicked.connect(self._on_delete_clicked)
        button_layout.addWidget(delete_button)

        layout.addLayout(button_layout)

    def _update_selection_count(self):
        """Update the 'Selected: X of Y' label."""
        count = sum(1 for cb in self._checkboxes if cb.isChecked())
        self._count_label.setText(f"Selected: {count} of {len(self._serial_numbers)}")

    def _on_delete_clicked(self):
        """Validate and accept the dialog."""
        selected = self.get_selected_serial_numbers()
        notes = self.notes_edit.text().strip()

        if not selected:
            QMessageBox.warning(
                self,
                tr("message.validation_error"),
                tr("error.no_serial_selected"),
            )
            return

        if len(selected) == len(self._serial_numbers):
            QMessageBox.warning(
                self,
                tr("message.validation_error"),
                tr("error.cannot_delete_all_serials"),
            )
            return

        if not notes:
            QMessageBox.warning(
                self,
                tr("message.validation_error"),
                tr("label.notes_reason"),
            )
            self.notes_edit.setFocus()
            return

        # Confirm
        confirm_text = tr("dialog.remove_serial.confirm").replace(
            "{count}", str(len(selected))
        )
        reply = QMessageBox.question(
            self,
            tr("dialog.remove_serial.title"),
            confirm_text,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.accept()

    def get_selected_serial_numbers(self) -> list[str]:
        """Return list of selected serial numbers."""
        return [cb.text() for cb in self._checkboxes if cb.isChecked()]

    def get_notes(self) -> str:
        """Return the entered notes/reason."""
        return self.notes_edit.text().strip()
