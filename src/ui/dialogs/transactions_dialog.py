"""Dialog for viewing transaction history."""

from datetime import datetime, timedelta
from typing import List, Optional

from PyQt6.QtCore import QDate, Qt
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QDateEdit,
    QDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from core.logger import logger
from core.repositories import LocationRepository
from ui.styles import apply_button_style
from ui.translations import format_quantity_change, tr


class TransactionsDialog(QDialog):
    """Dialog for displaying transaction history."""

    def __init__(
        self,
        item_type_id: int,
        item_name: str = "",
        item_is_serialized: bool = False,
        parent=None,
    ):
        super().__init__(parent)
        self._item_type_id = item_type_id
        self._item_name = item_name
        self._transactions_callback = None
        self._item_is_serialized = item_is_serialized
        self._setup_ui()

    def _setup_ui(self):
        """Set up the dialog UI."""
        title = tr("dialog.transactions.title")
        if self._item_name:
            title = f"{title} - {self._item_name}"
        self.setWindowTitle(title)
        self.setMinimumWidth(700)
        self.setMinimumHeight(400)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Header
        header_label = QLabel(tr("dialog.transactions.title"))
        header_font = QFont()
        header_font.setPointSize(14)
        header_font.setBold(True)
        header_label.setFont(header_font)
        header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header_label)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)

        # Date filter group
        filter_group = QGroupBox()
        filter_layout = QHBoxLayout(filter_group)

        # Start date
        start_label = QLabel(tr("transaction.filter.start_date"))
        filter_layout.addWidget(start_label)

        self.start_date_edit = QDateEdit()
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setDate(QDate.currentDate().addMonths(-1))
        self.start_date_edit.setDisplayFormat("yyyy-MM-dd")
        filter_layout.addWidget(self.start_date_edit)

        filter_layout.addSpacing(20)

        # End date
        end_label = QLabel(tr("transaction.filter.end_date"))
        filter_layout.addWidget(end_label)

        self.end_date_edit = QDateEdit()
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setDate(QDate.currentDate())
        self.end_date_edit.setDisplayFormat("yyyy-MM-dd")
        filter_layout.addWidget(self.end_date_edit)

        filter_layout.addStretch()

        # Apply filter button
        apply_button = QPushButton(tr("transaction.filter.apply"))
        apply_button_style(apply_button, "info")
        apply_button.clicked.connect(self._on_apply_filter)
        filter_layout.addWidget(apply_button)

        layout.addWidget(filter_group)

        # Transactions table
        # Columns: Date, Type, [Serial], Change, Before, After, Notes, From Location, To Location
        col_count = 9 if self._item_is_serialized else 8
        self.table = QTableWidget()
        self.table.setColumnCount(col_count)
        horizontal_header_labels = [
            tr("transaction.column.date"),
            tr("transaction.column.type"),
        ]
        if self._item_is_serialized:
            horizontal_header_labels.append(tr("field.serial_number"))
        horizontal_header_labels += [
            tr("transaction.column.change"),
            tr("transaction.column.before"),
            tr("transaction.column.after"),
            tr("transaction.column.notes"),
            tr("transaction.column.from_location"),
            tr("transaction.column.to_location"),
        ]
        self.table.setHorizontalHeaderLabels(horizontal_header_labels)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)

        # Set column widths
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        if self._item_is_serialized:
            header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(8, QHeaderView.ResizeMode.ResizeToContents)
        else:
            header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)

        layout.addWidget(self.table)

        # Close button
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        close_button = QPushButton(tr("button.close"))
        apply_button_style(close_button, "info")
        close_button.clicked.connect(self.accept)
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)

    def set_transactions_callback(self, callback):
        """Set the callback for getting transactions.

        Args:
            callback: Function(type_id, start_date, end_date) -> List[dict]
        """
        self._transactions_callback = callback
        self._load_transactions()

    def _on_apply_filter(self):
        """Handle apply filter button click."""
        self._load_transactions()

    def _load_transactions(self):
        """Load transactions based on current filter settings."""
        if not self._transactions_callback:
            return

        start_date = self.start_date_edit.date().toPyDate()
        end_date = self.end_date_edit.date().toPyDate()

        # Convert to datetime with time
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())

        try:
            transactions = self._transactions_callback(
                self._item_type_id, start_datetime, end_datetime
            )
            loc_map = {loc.id: loc.name for loc in LocationRepository.get_all()}
            self._populate_table(transactions, loc_map)
        except Exception as e:
            logger.error(f"Failed to load transactions: {e}", exc_info=True)
            self.table.setRowCount(0)
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                tr("error.generic.title"),
                f"{tr('error.generic.message')}\n{e}",
            )

    def _populate_table(self, transactions: List[dict], loc_map: dict = None):
        """Populate the table with transaction data."""
        if loc_map is None:
            loc_map = {}
        self.table.setRowCount(len(transactions))

        for row, trans in enumerate(transactions):
            column = 0

            def cell(text: str, col: int, color: QColor = None):
                item = QTableWidgetItem(text)
                if color:
                    item.setForeground(color)
                self.table.setItem(row, col, item)

            trans_type = trans["type"]
            if trans_type == "add":
                type_color = QColor(0, 128, 0)    # Green
            elif trans_type == "edit":
                type_color = QColor(0, 0, 192)    # Blue
            elif trans_type == "transfer":
                type_color = QColor(80, 0, 160)   # Purple
            else:
                type_color = QColor(192, 0, 0)    # Red

            # Date
            cell(
                trans["created_at"].strftime("%Y-%m-%d %H:%M") if trans["created_at"] else "",
                column,
            )
            column += 1

            # Type
            cell(tr(f"transaction.type.{trans_type}"), column, type_color)
            column += 1

            if self._item_is_serialized:
                # Serial Number
                cell(trans.get("serial_number") or "—", column)
                column += 1

            # Change
            cell(format_quantity_change(trans), column, type_color)
            column += 1

            # Before / After
            cell(str(trans["quantity_before"]), column)
            column += 1
            cell(str(trans["quantity_after"]), column)
            column += 1

            # Notes
            cell(trans.get("notes") or "", column)
            column += 1

            # From Location
            from_id = trans.get("from_location_id")
            cell(loc_map.get(from_id, "") if from_id else "", column)
            column += 1

            # To Location
            to_id = trans.get("to_location_id")
            cell(loc_map.get(to_id, "") if to_id else "", column)
