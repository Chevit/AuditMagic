"""Search widget with autocomplete dropdown and history."""
from typing import Optional, List
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLineEdit, QComboBox,
    QPushButton, QCompleter, QListWidget, QListWidgetItem, QLabel
)
from PyQt6.QtGui import QFont
from ui_entities.translations import tr


class SearchWidget(QWidget):
    """Search widget with autocomplete and history."""

    # Signals
    search_requested = pyqtSignal(str, str)  # query, field (or None for all)
    search_cleared = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._autocomplete_callback = None
        self._history_callback = None
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
        search_row.addWidget(self.field_combo)

        # Search input with autocomplete
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(tr("placeholder.search"))
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._on_text_changed)
        self.search_input.returnPressed.connect(self._on_search_clicked)
        search_row.addWidget(self.search_input, 1)

        # Completer for autocomplete
        self.completer = QCompleter([])
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchFlag.MatchContains)
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

        # History section (collapsible)
        self.history_widget = QWidget()
        history_layout = QVBoxLayout(self.history_widget)
        history_layout.setContentsMargins(0, 5, 0, 0)
        history_layout.setSpacing(2)

        history_label = QLabel(tr("label.recent_searches"))
        history_font = QFont()
        history_font.setPointSize(9)
        history_label.setFont(history_font)
        history_layout.addWidget(history_label)

        self.history_list = QListWidget()
        self.history_list.setMaximumHeight(100)
        self.history_list.itemClicked.connect(self._on_history_item_clicked)
        history_layout.addWidget(self.history_list)

        self.history_widget.setVisible(False)
        layout.addWidget(self.history_widget)

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
        self._update_history()

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
            self._update_completer(suggestions)

    def _update_completer(self, suggestions: List[str]):
        """Update the completer with new suggestions."""
        from PyQt6.QtCore import QStringListModel
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

    def _on_history_item_clicked(self, item: QListWidgetItem):
        """Handle history item click."""
        data = item.data(Qt.ItemDataRole.UserRole)
        if data:
            query, field = data
            self.search_input.setText(query)
            # Set the field combo
            for i in range(self.field_combo.count()):
                if self.field_combo.itemData(i) == field:
                    self.field_combo.setCurrentIndex(i)
                    break
            self._on_search_clicked()

    def _update_history(self):
        """Update the history list from callback."""
        if not self._history_callback:
            return

        history = self._history_callback()
        self.history_list.clear()

        if history:
            self.history_widget.setVisible(True)
            for query, field in history:
                field_name = tr("search.all_fields") if not field else tr(f"search.field.{field}")
                item = QListWidgetItem(f"{query} ({field_name})")
                item.setData(Qt.ItemDataRole.UserRole, (query, field))
                self.history_list.addItem(item)
        else:
            self.history_widget.setVisible(False)

    def refresh_history(self):
        """Refresh the history list."""
        self._update_history()

    def show_history(self, show: bool = True):
        """Show or hide the history section."""
        self.history_widget.setVisible(show and self.history_list.count() > 0)

    def get_current_query(self) -> str:
        """Get the current search query."""
        return self.search_input.text().strip()

    def get_current_field(self) -> Optional[str]:
        """Get the current search field."""
        return self.field_combo.currentData()
