"""Transfer items between storage locations."""

from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from services import InventoryService, LocationService
from styles import apply_button_style, apply_combo_box_style, apply_input_style
from ui_entities.translations import tr

try:
    from PyQt6.QtWidgets import QComboBox
except ImportError:
    pass


class TransferDialog(QDialog):
    """Dialog for transferring items (or specific serial numbers) to another location."""

    def __init__(self, item, current_location_id: Optional[int], parent=None):
        super().__init__(parent)
        self._item = item
        self._is_serialized = item.is_serialized
        self._item_type_id = item.item_type_id

        # Determine source location
        if current_location_id is not None:
            self._source_id = current_location_id
            self._needs_source_combo = False
        elif not getattr(item, "is_multi_location", False) and getattr(item, "location_id", None):
            self._source_id = item.location_id
            self._needs_source_combo = False
        else:
            # Multi-location item in "All Locations" view — user must pick source
            self._source_id = None
            self._needs_source_combo = True

        self._all_locs = LocationService.get_all_locations()
        self._loc_map = {loc.id: loc.name for loc in self._all_locs}

        self._setup_ui()
        self._populate()

    # ------------------------------------------------------------------ #
    #  UI Construction                                                     #
    # ------------------------------------------------------------------ #

    def _setup_ui(self):
        self.setWindowTitle(tr("transfer.title"))
        self.setMinimumWidth(440)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Item name header
        item_name = (
            f"{self._item.item_type} — {self._item.sub_type}"
            if self._item.sub_type
            else self._item.item_type
        )
        header = QLabel(f"<b>{item_name}</b>")
        layout.addWidget(header)

        # Source row
        src_row = QHBoxLayout()
        src_row.addWidget(QLabel(tr("transfer.source")))
        if self._needs_source_combo:
            self.source_combo = QComboBox()
            apply_combo_box_style(self.source_combo)
            src_row.addWidget(self.source_combo, stretch=1)
        else:
            self._source_label = QLabel(self._loc_map.get(self._source_id, ""))
            src_row.addWidget(self._source_label, stretch=1)
        layout.addLayout(src_row)

        # Destination row
        dest_row = QHBoxLayout()
        dest_row.addWidget(QLabel(tr("transfer.destination")))
        self.dest_combo = QComboBox()
        apply_combo_box_style(self.dest_combo)
        dest_row.addWidget(self.dest_combo, stretch=1)
        layout.addLayout(dest_row)

        # Content: qty or serials
        if self._is_serialized:
            layout.addWidget(QLabel(tr("transfer.select_serials")))
            self.serial_list = QListWidget()
            self.serial_list.setMaximumHeight(200)
            layout.addWidget(self.serial_list)
            self.selected_label = QLabel(
                tr("transfer.selected_count").format(selected=0, total=0)
            )
            layout.addWidget(self.selected_label)
        else:
            qty_row = QHBoxLayout()
            qty_row.addWidget(QLabel(tr("transfer.quantity")))
            self.qty_spin = QSpinBox()
            self.qty_spin.setMinimum(1)
            qty_row.addWidget(self.qty_spin)
            self.avail_label = QLabel("")
            qty_row.addWidget(self.avail_label)
            qty_row.addStretch()
            layout.addLayout(qty_row)

        # Notes
        notes_row = QHBoxLayout()
        notes_row.addWidget(QLabel(tr("transfer.notes")))
        self.notes_edit = QLineEdit()
        apply_input_style(self.notes_edit)
        notes_row.addWidget(self.notes_edit, stretch=1)
        layout.addLayout(notes_row)

        # Error label
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: red;")
        self.error_label.hide()
        layout.addWidget(self.error_label)

        # Buttons
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.button(QDialogButtonBox.StandardButton.Ok).setText(tr("transfer.button"))
        apply_button_style(btns.button(QDialogButtonBox.StandardButton.Ok), "primary")
        apply_button_style(btns.button(QDialogButtonBox.StandardButton.Cancel), "secondary")
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    # ------------------------------------------------------------------ #
    #  Population                                                          #
    # ------------------------------------------------------------------ #

    def _populate(self):
        if self._needs_source_combo:
            self._populate_source_combo()
            self.source_combo.currentIndexChanged.connect(self._on_source_changed)
            if self.source_combo.count() > 0:
                self._source_id = self.source_combo.currentData()

        self._populate_dest_combo()
        self._populate_content()

    def _populate_source_combo(self):
        locs = LocationService.get_locations_for_type(self._item_type_id)
        for loc in locs:
            self.source_combo.addItem(loc.name, userData=loc.id)

    def _populate_dest_combo(self):
        self.dest_combo.clear()
        for loc in self._all_locs:
            if loc.id != self._source_id:
                self.dest_combo.addItem(loc.name, userData=loc.id)

    def _populate_content(self):
        if self._source_id is None:
            return

        total_qty, serials, item_ids = InventoryService.get_type_items_at_location(
            self._item_type_id, self._source_id
        )

        if self._is_serialized:
            self.serial_list.clear()
            for sn in serials:
                list_item = QListWidgetItem(sn)
                list_item.setFlags(list_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                list_item.setCheckState(Qt.CheckState.Unchecked)
                self.serial_list.addItem(list_item)
            self.serial_list.itemChanged.connect(self._update_selected_count)
            self._update_selected_count()
        else:
            max_qty = max(total_qty, 1)
            self.qty_spin.setMaximum(max_qty)
            self.qty_spin.setValue(1)
            self.avail_label.setText(tr("transfer.available").format(count=total_qty))

    # ------------------------------------------------------------------ #
    #  Slots                                                               #
    # ------------------------------------------------------------------ #

    def _on_source_changed(self):
        self._source_id = self.source_combo.currentData()
        self._populate_dest_combo()
        if self._is_serialized:
            self.serial_list.itemChanged.disconnect(self._update_selected_count)
        self._populate_content()

    def _update_selected_count(self):
        total = self.serial_list.count()
        selected = sum(
            1
            for i in range(total)
            if self.serial_list.item(i).checkState() == Qt.CheckState.Checked
        )
        self.selected_label.setText(
            tr("transfer.selected_count").format(selected=selected, total=total)
        )

    # ------------------------------------------------------------------ #
    #  Validation & Accept                                                 #
    # ------------------------------------------------------------------ #

    def _on_accept(self):
        self.error_label.hide()

        dest_id = self.dest_combo.currentData()
        if dest_id is None:
            self.error_label.setText(tr("transfer.error.no_destination"))
            self.error_label.show()
            return

        if self._source_id == dest_id:
            self.error_label.setText(tr("transfer.error.same_location"))
            self.error_label.show()
            return

        notes = self.notes_edit.text().strip()

        try:
            if self._is_serialized:
                selected_serials = [
                    self.serial_list.item(i).text()
                    for i in range(self.serial_list.count())
                    if self.serial_list.item(i).checkState() == Qt.CheckState.Checked
                ]
                if not selected_serials:
                    self.error_label.setText(tr("transfer.error.no_serials"))
                    self.error_label.show()
                    return
                InventoryService.transfer_serialized_items(
                    serial_numbers=selected_serials,
                    from_location_id=self._source_id,
                    to_location_id=dest_id,
                    notes=notes,
                )
            else:
                quantity = self.qty_spin.value()
                if quantity <= 0:
                    self.error_label.setText(tr("transfer.error.no_quantity"))
                    self.error_label.show()
                    return
                _, _, item_ids = InventoryService.get_type_items_at_location(
                    self._item_type_id, self._source_id
                )
                if not item_ids:
                    self.error_label.setText(tr("error.generic.message"))
                    self.error_label.show()
                    return
                InventoryService.transfer_item(
                    item_id=item_ids[0],
                    quantity=quantity,
                    from_location_id=self._source_id,
                    to_location_id=dest_id,
                    notes=notes,
                )
            self.accept()
        except Exception as e:
            self.error_label.setText(str(e))
            self.error_label.show()
