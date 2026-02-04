"""Search widget with autocomplete dropdown and history."""
from typing import Optional, List, Tuple
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QStringListModel
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLineEdit, QComboBox,
    QPushButton, QCompleter
)
from ui_entities.translations import tr


class SearchWidget(QWidget):
    """Search widget with autocomplete and history integrated in QCompleter."""

    # Signals
    search_requested = pyqtSignal(str, str)  # query, field (or None for all)
    search_cleared = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._autocomplete_callback = None
        self._history_callback = None
        self._history_items: List[Tuple[str, Optional[str]]] = []
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
        self.field_combo.addItem(tr("search.field.notes"), "notes")
        self.field_combo.setMinimumWidth(120)
        self.field_combo.currentIndexChanged.connect(self._on_field_changed)
        search_row.addWidget(self.field_combo)

        # Search input with autocomplete
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(tr("placeholder.search"))
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._on_text_changed)
        self.search_input.returnPressed.connect(self._on_search_clicked)
        search_row.addWidget(self.search_input, 1)

        # Completer for autocomplete and history
        self.completer = QCompleter([])
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.completer.activated.connect(self._on_completer_activated)
        self.search_input.setCompleter(self.completer)

        # Search button
        self.search_button = QPushButton(tr("button.search"))
        self.search_button.clicked.connect(self._on_search_clicked)
        search_row.addWidget(self.search_button)

        # Clear button
        self.clear_button = QPushButton(tr("button.clear"))
        self.clear_button.clicked.connect(self._on_clear_clicked)
        search_row.addWidget(self.clear_button)

        layout.addLayout(search_row)

    def set_autocomplete_callback(self, callback):
        """Set the callback for getting autocomplete suggestions.

        Args:
            callback: Function(prefix: str, field: str) -> List[str]
        """
        self._autocomplete_callback = callback

    def set_history_callback(self, callback):
        """Set the callback for getting search history.

        Args:
            callback: Function() -> List[Tuple[str, Optional[str]]]
        """
        self._history_callback = callback
        self._load_history()

    def _load_history(self):
        """Load history items from callback."""
        if self._history_callback:
            self._history_items = self._history_callback()

    def _on_field_changed(self, index: int):
        """Handle field combo change - update completer with history."""
        self._update_completer_with_history_and_suggestions()

    def _on_text_changed(self, text: str):
        """Handle text changes for autocomplete with debounce."""
        self._debounce_timer.stop()
        if len(text) >= 1:
            self._debounce_timer.start(150)  # 150ms debounce
        else:
            # Show history when input is empty
            self._update_completer_with_history_and_suggestions()

    def _on_debounce_timeout(self):
        """Handle debounce timeout - fetch autocomplete suggestions."""
        self._update_completer_with_history_and_suggestions()

    def _update_completer_with_history_and_suggestions(self):
        """Update completer with both history and autocomplete suggestions."""
        text = self.search_input.text()
        field = self.field_combo.currentData()
        suggestions = []

        # Get history items that match current field
        history_queries = self._get_filtered_history_queries(field)

        # Get autocomplete suggestions if there's text
        if self._autocomplete_callback and len(text) >= 1:
            autocomplete = self._autocomplete_callback(text, field)
            # Combine history and autocomplete, removing duplicates
            suggestions = history_queries + [s for s in autocomplete if s not in history_queries]
        else:
            suggestions = history_queries

        model = QStringListModel(suggestions)
        self.completer.setModel(model)

    def _get_filtered_history_queries(self, current_field: Optional[str]) -> List[str]:
        """Get history queries filtered by current field.

        Args:
            current_field: The currently selected search field (None for all fields)

        Returns:
            List of query strings from history matching the field
        """
        queries = []
        for query, field in self._history_items:
            # Include if fields match, or if current field is "all" (None)
            if current_field is None or field == current_field:
                if query not in queries:
                    queries.append(query)
        return queries

    def _on_completer_activated(self, text: str):
        """Handle completer item selection."""
        # Trigger search when item is selected from completer
        self._on_search_clicked()

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

    def refresh_history(self):
        """Refresh the history from callback."""
        self._load_history()
        self._update_completer_with_history_and_suggestions()

    def get_current_query(self) -> str:
        """Get the current search query."""
        return self.search_input.text().strip()

    def get_current_field(self) -> Optional[str]:
        """Get the current search field."""
        return self.field_combo.currentData()
