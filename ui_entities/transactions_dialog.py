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

from styles import apply_button_style
from ui_entities.translations import tr


class TransactionsDialog(QDialog):
    """Dialog for displaying transaction history."""

    def __init__(
        self,
        item_type_id: int,
        item_name: str = "",
        parent=None,
    ):
        super().__init__(parent)
        self._item_type_id = item_type_id
        self._item_name = item_name
        self._transactions_callback = None
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
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            [
                tr("transaction.column.date"),
                tr("transaction.column.type"),
                tr("field.serial_number"),
                tr("transaction.column.change"),
                tr("transaction.column.before"),
                tr("transaction.column.after"),
                tr("transaction.column.notes"),
            ]
        )
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
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)

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

        transactions = self._transactions_callback(
            self._item_type_id, start_datetime, end_datetime
        )
        self._populate_table(transactions)

    def _populate_table(self, transactions: List[dict]):
        """Populate the table with transaction data."""
        self.table.setRowCount(len(transactions))

        for row, trans in enumerate(transactions):
            # Date
            date_item = QTableWidgetItem(
                trans["created_at"].strftime("%Y-%m-%d %H:%M")
                if trans["created_at"]
                else ""
            )
            self.table.setItem(row, 0, date_item)

            # Type
            trans_type = trans["type"]
            type_text = tr(f"transaction.type.{trans_type}")
            type_item = QTableWidgetItem(type_text)
            if trans_type == "add":
                type_item.setForeground(QColor(0, 128, 0))  # Green
            elif trans_type == "edit":
                type_item.setForeground(QColor(0, 0, 192))  # Blue
            else:
                type_item.setForeground(QColor(192, 0, 0))  # Red
            self.table.setItem(row, 1, type_item)

            # Serial Number
            serial = trans.get("serial_number", "") or "—"
            serial_item = QTableWidgetItem(serial)
            self.table.setItem(row, 2, serial_item)

            # Change
            change = trans["quantity_change"]
            if trans_type == "edit":
                change_text = "—"
            elif trans_type == "add":
                change_text = f"+{change}"
            else:
                change_text = f"-{change}"
            change_item = QTableWidgetItem(change_text)
            if trans_type == "add":
                change_item.setForeground(QColor(0, 128, 0))
            elif trans_type == "edit":
                change_item.setForeground(QColor(0, 0, 192))
            else:
                change_item.setForeground(QColor(192, 0, 0))
            self.table.setItem(row, 3, change_item)

            # Before
            before_item = QTableWidgetItem(str(trans["quantity_before"]))
            self.table.setItem(row, 4, before_item)

            # After
            after_item = QTableWidgetItem(str(trans["quantity_after"]))
            self.table.setItem(row, 5, after_item)

            # Notes
            notes_item = QTableWidgetItem(trans.get("notes", "") or "")
            self.table.setItem(row, 6, notes_item)
