"""Dialog showing all transactions across all item types, filterable by location."""

from datetime import datetime
from typing import Optional

from PyQt6.QtCore import QDate, Qt
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
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
from core.services import InventoryService, TransactionService
from ui.styles import apply_button_style, apply_combo_box_style
from ui.translations import format_quantity_change, tr


class AllTransactionsDialog(QDialog):
    """Dialog for viewing all transactions with optional location filter."""

    def __init__(self, current_location_id: Optional[int] = None, parent=None):
        super().__init__(parent)
        self._initial_location_id = current_location_id
        self._setup_ui()
        self._load_transactions()

    # ------------------------------------------------------------------ #
    #  UI                                                                  #
    # ------------------------------------------------------------------ #

    def _setup_ui(self):
        self.setWindowTitle(tr("dialog.all_transactions.title"))
        self.setMinimumWidth(900)
        self.setMinimumHeight(520)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Header
        header = QLabel(tr("dialog.all_transactions.title"))
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        header.setFont(font)
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(sep)

        # Filter group
        filter_group = QGroupBox()
        filter_layout = QHBoxLayout(filter_group)

        # Location filter
        filter_layout.addWidget(QLabel(tr("dialog.all_transactions.location_filter")))
        self.loc_combo = QComboBox()
        apply_combo_box_style(self.loc_combo)
        self.loc_combo.setMinimumWidth(180)
        self._populate_location_combo()
        filter_layout.addWidget(self.loc_combo)

        filter_layout.addSpacing(20)

        # Date range
        filter_layout.addWidget(QLabel(tr("transaction.filter.start_date")))
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate.currentDate().addMonths(-1))
        self.start_date.setDisplayFormat("yyyy-MM-dd")
        filter_layout.addWidget(self.start_date)

        filter_layout.addSpacing(10)

        filter_layout.addWidget(QLabel(tr("transaction.filter.end_date")))
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setDisplayFormat("yyyy-MM-dd")
        filter_layout.addWidget(self.end_date)

        filter_layout.addStretch()

        apply_btn = QPushButton(tr("transaction.filter.apply"))
        apply_button_style(apply_btn, "info")
        apply_btn.clicked.connect(self._load_transactions)
        filter_layout.addWidget(apply_btn)

        layout.addWidget(filter_group)

        # Table
        self.table = QTableWidget()
        self._setup_table()
        layout.addWidget(self.table)

        # Footer
        footer = QHBoxLayout()
        footer.addStretch()
        close_btn = QPushButton(tr("button.close"))
        apply_button_style(close_btn, "info")
        close_btn.clicked.connect(self.accept)
        footer.addWidget(close_btn)
        layout.addLayout(footer)

    def _populate_location_combo(self):
        self.loc_combo.clear()
        self.loc_combo.addItem(tr("location.all"), userData=None)
        for loc in LocationRepository.get_all():
            self.loc_combo.addItem(loc.name, userData=loc.id)
        # Pre-select to the current location
        if self._initial_location_id is not None:
            for i in range(self.loc_combo.count()):
                if self.loc_combo.itemData(i) == self._initial_location_id:
                    self.loc_combo.setCurrentIndex(i)
                    break

    def _setup_table(self):
        columns = [
            tr("transaction.column.date"),
            tr("transaction.column.type"),
            tr("transaction.column.item_type"),
            tr("field.serial_number"),
            tr("transaction.column.change"),
            tr("transaction.column.before"),
            tr("transaction.column.after"),
            tr("transaction.column.notes"),
            tr("transaction.column.from_location"),
            tr("transaction.column.to_location"),
        ]
        self.table.setColumnCount(len(columns))
        self.table.setHorizontalHeaderLabels(columns)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(9, QHeaderView.ResizeMode.ResizeToContents)

    # ------------------------------------------------------------------ #
    #  Data loading                                                        #
    # ------------------------------------------------------------------ #

    def _load_transactions(self):
        start_date = self.start_date.date().toPyDate()
        end_date = self.end_date.date().toPyDate()
        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.max.time())

        location_id = self.loc_combo.currentData()

        try:
            if location_id is not None:
                transactions = TransactionService.get_transactions_by_location_and_date_range(
                    location_id, start_dt, end_dt
                )
            else:
                transactions = TransactionService.get_all_transactions_by_date_range(
                    start_dt, end_dt
                )

            # Build lookup maps for names
            type_map = InventoryService.get_item_type_display_names()
            loc_map = {loc.id: loc.name for loc in LocationRepository.get_all()}

            self._populate_table(transactions, type_map, loc_map)
        except Exception as e:
            logger.error(f"Failed to load all transactions: {e}", exc_info=True)
            self.table.setRowCount(0)

    def _populate_table(self, transactions: list, type_map: dict, loc_map: dict):
        self.table.setRowCount(len(transactions))

        for row, trans in enumerate(transactions):
            trans_type = trans["type"]

            # Colour helper
            if trans_type == "add":
                color = QColor(0, 128, 0)
            elif trans_type in ("edit",):
                color = QColor(0, 0, 192)
            elif trans_type == "transfer":
                color = QColor(80, 0, 160)
            else:
                color = QColor(192, 0, 0)

            def cell(text: str, col: int, clr: QColor = None):
                item = QTableWidgetItem(text)
                if clr:
                    item.setForeground(clr)
                self.table.setItem(row, col, item)

            # 0 Date
            cell(
                trans["created_at"].strftime("%Y-%m-%d %H:%M") if trans["created_at"] else "",
                0,
            )
            # 1 Type
            type_label = tr(f"transaction.type.{trans_type}")
            cell(type_label, 1, color)
            # 2 Item type
            cell(type_map.get(trans["item_type_id"], str(trans["item_type_id"])), 2)
            # 3 Serial
            cell(trans.get("serial_number") or "", 3)
            # 4 Change
            cell(format_quantity_change(trans), 4, color)
            # 5 Before
            cell(str(trans["quantity_before"]), 5)
            # 6 After
            cell(str(trans["quantity_after"]), 6)
            # 7 Notes
            cell(trans.get("notes") or "", 7)
            # 8 From location
            from_id = trans.get("from_location_id")
            cell(loc_map.get(from_id, "") if from_id else "", 8)
            # 9 To location
            to_id = trans.get("to_location_id")
            cell(loc_map.get(to_id, "") if to_id else "", 9)
