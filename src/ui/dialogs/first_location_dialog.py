"""First-launch mandatory location creation dialog.

Shown when the app starts with no locations in the database.
Cannot be dismissed without creating a location.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
)

from core.repositories import LocationRepository
from ui.styles import apply_button_style, apply_input_style
from ui.translations import tr


class FirstLocationDialog(QDialog):
    """Mandatory dialog to create the first storage location on first launch."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._location_id: int = None
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle(tr("location.first_launch.title"))
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowType.WindowCloseButtonHint
        )
        self.setMinimumWidth(380)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        msg = QLabel(tr("location.first_launch.message"))
        msg.setWordWrap(True)
        layout.addWidget(msg)

        name_label = QLabel(tr("location.name"))
        layout.addWidget(name_label)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText(tr("location.name.placeholder"))
        apply_input_style(self.name_edit)
        layout.addWidget(self.name_edit)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: red;")
        self.error_label.hide()
        layout.addWidget(self.error_label)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        apply_button_style(buttons.button(QDialogButtonBox.StandardButton.Ok), "primary")
        buttons.accepted.connect(self._on_accept)
        layout.addWidget(buttons)

    def _on_accept(self):
        name = self.name_edit.text().strip()
        if not name:
            self.error_label.setText(tr("location.error.name_required"))
            self.error_label.show()
            return

        # Check for duplicate
        if LocationRepository.get_by_name(name):
            self.error_label.setText(tr("location.error.name_exists"))
            self.error_label.show()
            return

        try:
            loc = LocationRepository.create(name)
            self._location_id = loc.id
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, tr("error.generic.title"), str(e))

    def get_location_id(self) -> int:
        """Return the ID of the newly created location."""
        return self._location_id
