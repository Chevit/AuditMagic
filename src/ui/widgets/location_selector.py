"""Location selector widget — dropdown + manage button shown above the inventory list."""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QPushButton, QWidget

from core.repositories import LocationRepository
from ui.styles import apply_button_style, apply_combo_box_style
from ui.translations import tr


class LocationSelectorWidget(QWidget):
    """Horizontal bar with a location dropdown and a Manage button.

    Signals:
        location_changed(int | None): Emitted when the user changes the location.
            Carries the selected location_id, or None for "All Locations".
        manage_requested(): Emitted when the user clicks the Manage button.
    """

    location_changed = pyqtSignal(object)  # int | None
    manage_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._suppress_signal = False
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        label = QLabel(tr("location.title"))
        layout.addWidget(label)

        self.combo = QComboBox()
        self.combo.setMinimumWidth(180)
        apply_combo_box_style(self.combo)
        layout.addWidget(self.combo, stretch=1)

        self.manage_btn = QPushButton(tr("location.manage"))
        apply_button_style(self.manage_btn, "secondary")
        layout.addWidget(self.manage_btn)

        self.combo.currentIndexChanged.connect(self._on_index_changed)
        self.manage_btn.clicked.connect(self.manage_requested.emit)

        self.refresh_locations()

    def refresh_locations(self):
        """Reload locations from the DB and repopulate the dropdown."""
        self._suppress_signal = True
        try:
            current_id = self.current_location_id()
            self.combo.clear()
            # First entry: "All Locations" (maps to None)
            self.combo.addItem(tr("location.all"), userData=None)
            for loc in LocationRepository.get_all():
                self.combo.addItem(loc.name, userData=loc.id)
            # Try to restore previously selected item
            self.set_current_location(current_id)
        finally:
            self._suppress_signal = False

    def set_current_location(self, location_id):
        """Set the dropdown to a specific location without emitting location_changed.

        Args:
            location_id: The Location ID to select, or None for "All Locations".
        """
        self._suppress_signal = True
        try:
            for i in range(self.combo.count()):
                if self.combo.itemData(i) == location_id:
                    self.combo.setCurrentIndex(i)
                    return
            # Fallback: select "All Locations"
            self.combo.setCurrentIndex(0)
        finally:
            self._suppress_signal = False

    def current_location_id(self):
        """Return the currently selected location_id, or None for "All Locations"."""
        return self.combo.currentData()

    def _on_index_changed(self):
        if not self._suppress_signal:
            self.location_changed.emit(self.combo.currentData())

    def reapply_styles(self):
        """Re-apply theme-aware styles after a theme switch."""
        apply_combo_box_style(self.combo)
        apply_button_style(self.manage_btn, "secondary")
