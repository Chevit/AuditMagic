"""Search widget with autocomplete dropdown."""

from typing import Optional, List
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QStringListModel
from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLineEdit,
    QComboBox,
    QPushButton,
    QCompleter,
)
from ui_entities.translations import tr
from styles import apply_input_style, apply_button_style, apply_combo_box_style


class SearchWidget(QWidget):
    """Search widget with autocomplete."""

    # Signals
    search_requested = pyqtSignal(str, str)  # query, field (or None for all)
    search_cleared = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._autocomplete_callback = None
        self._debounce_timer = QTimer()
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.timeout.connect(self._on_debounce_timeout)
        self._setup_ui()

    def _setup_ui(self):
        """Set up the search widget UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # Search row
        search_row = QHBoxLayout()
        search_row.setSpacing(10)

        # Search field selector
        self.field_combo = QComboBox()
        self.field_combo.addItem(tr("search.all_fields"), None)
        self.field_combo.addItem(tr("search.field.item_type"), "item_type")
        self.field_combo.addItem(tr("search.field.sub_type"), "sub_type")
        self.field_combo.addItem(tr("search.field.details"), "details")
        self.field_combo.setMinimumWidth(120)
        apply_combo_box_style(self.field_combo)
        search_row.addWidget(self.field_combo)

        # Search input with autocomplete
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(tr("placeholder.search"))
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._on_text_changed)
        self.search_input.returnPressed.connect(self._on_search_clicked)
        apply_input_style(self.search_input)
        search_row.addWidget(self.search_input, 1)

        # Completer for autocomplete
        self.completer = QCompleter([])
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.search_input.setCompleter(self.completer)

        # Search button
        self.search_button = QPushButton(tr("button.search"))
        apply_button_style(self.search_button, "info")
        self.search_button.clicked.connect(self._on_search_clicked)
        search_row.addWidget(self.search_button)

        # Clear button
        self.clear_button = QPushButton(tr("button.clear"))
        apply_button_style(self.clear_button, "secondary")
        self.clear_button.clicked.connect(self._on_clear_clicked)
        search_row.addWidget(self.clear_button)

        layout.addLayout(search_row)

    def set_autocomplete_callback(self, callback):
        """Set the callback for getting autocomplete suggestions.

        Args:
            callback: Function(prefix: str, field: str) -> List[str]
        """
        self._autocomplete_callback = callback

    def _on_text_changed(self, text: str):
        """Handle text changes for autocomplete with debounce."""
        self._debounce_timer.stop()
        if len(text) >= 1:
            self._debounce_timer.start(150)  # 150ms debounce

    def _on_debounce_timeout(self):
        """Handle debounce timeout - fetch autocomplete suggestions."""
        text = self.search_input.text()
        if self._autocomplete_callback and len(text) >= 1:
            field = self.field_combo.currentData()
            suggestions = self._autocomplete_callback(text, field)
            model = QStringListModel(suggestions)
            self.completer.setModel(model)

    def _on_search_clicked(self):
        """Handle search button click."""
        query = self.search_input.text().strip()
        if query:
            field = self.field_combo.currentData()
            self.search_requested.emit(query, field if field else "")

    def _on_clear_clicked(self):
        """Handle clear button click."""
        self.search_input.clear()
        self.search_cleared.emit()

    def get_current_query(self) -> str:
        """Get the current search query."""
        return self.search_input.text().strip()

    def get_current_field(self) -> Optional[str]:
        """Get the current search field."""
        return self.field_combo.currentData()
