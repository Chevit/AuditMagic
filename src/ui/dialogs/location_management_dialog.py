"""Location management dialog — create, rename, delete locations."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QHBoxLayout,
                             QLabel, QLineEdit, QListWidget, QListWidgetItem,
                             QMessageBox, QPushButton, QVBoxLayout)

from core.repositories import LocationRepository
from core.services import InventoryService
from ui.styles import (apply_button_style, apply_combo_box_style,
                       apply_input_style)
from ui.translations import tr


class _AddRenameDialog(QDialog):
    """Small dialog for adding or renaming a location."""

    def __init__(self, title: str, initial_name: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(320)
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        layout.addWidget(QLabel(tr("location.name")))
        self.name_edit = QLineEdit(initial_name)
        self.name_edit.setPlaceholderText(tr("location.name.placeholder"))
        apply_input_style(self.name_edit)
        layout.addWidget(self.name_edit)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: red;")
        self.error_label.hide()
        layout.addWidget(self.error_label)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        apply_button_style(btns.button(QDialogButtonBox.StandardButton.Ok), "primary")
        apply_button_style(
            btns.button(QDialogButtonBox.StandardButton.Cancel), "secondary"
        )
        btns.accepted.connect(self._validate)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        self.name_edit.returnPressed.connect(self._validate)

    def _validate(self):
        if not self.name_edit.text().strip():
            self.error_label.setText(tr("location.error.name_required"))
            self.error_label.show()
            return
        self.accept()

    def get_name(self) -> str:
        return self.name_edit.text().strip()


class LocationManagementDialog(QDialog):
    """Dialog for managing locations: add, rename, delete."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("location.manage.title"))
        self.setMinimumWidth(460)
        self.setMinimumHeight(360)
        self._setup_ui()
        self._load_locations()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        self.list_widget = QListWidget()
        self.list_widget.currentRowChanged.connect(self._on_selection_changed)
        layout.addWidget(self.list_widget)

        btn_row = QHBoxLayout()

        self.add_btn = QPushButton(tr("location.add"))
        apply_button_style(self.add_btn, "primary")
        self.add_btn.clicked.connect(self._on_add)
        btn_row.addWidget(self.add_btn)

        self.rename_btn = QPushButton(tr("location.rename"))
        apply_button_style(self.rename_btn, "secondary")
        self.rename_btn.clicked.connect(self._on_rename)
        self.rename_btn.setEnabled(False)
        btn_row.addWidget(self.rename_btn)

        self.delete_btn = QPushButton(tr("location.delete"))
        apply_button_style(self.delete_btn, "danger")
        self.delete_btn.clicked.connect(self._on_delete)
        self.delete_btn.setEnabled(False)
        btn_row.addWidget(self.delete_btn)

        layout.addLayout(btn_row)

        close_btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_btns.rejected.connect(self.reject)
        layout.addWidget(close_btns)

    def _load_locations(self):
        self.list_widget.clear()
        for loc, count in LocationRepository.get_all_with_item_counts():
            item = QListWidgetItem(
                f"{loc.name}  —  {tr('location.item_count').format(count=count)}"
            )
            item.setData(Qt.ItemDataRole.UserRole, loc.id)
            self.list_widget.addItem(item)

    def _on_selection_changed(self, row: int):
        has = row >= 0
        self.rename_btn.setEnabled(has)
        self.delete_btn.setEnabled(has)

    def _selected_id(self):
        item = self.list_widget.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _on_add(self):
        dlg = _AddRenameDialog(tr("location.add.title"), parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        name = dlg.get_name()
        if LocationRepository.get_by_name(name):
            QMessageBox.warning(
                self, tr("error.generic.title"), tr("location.error.name_exists")
            )
            return
        try:
            LocationRepository.create(name)
            self._load_locations()
        except Exception as e:
            QMessageBox.critical(self, tr("error.generic.title"), str(e))

    def _on_rename(self):
        loc_id = self._selected_id()
        if not loc_id:
            return
        current_item = self.list_widget.currentItem()
        # Extract current name (before the " — " suffix)
        current_name = current_item.text().split("  —  ")[0].strip()
        dlg = _AddRenameDialog(
            tr("location.rename.title"), initial_name=current_name, parent=self
        )
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        new_name = dlg.get_name()
        if new_name == current_name:
            return
        existing = LocationRepository.get_by_name(new_name)
        if existing and existing.id != loc_id:
            QMessageBox.warning(
                self, tr("error.generic.title"), tr("location.error.name_exists")
            )
            return
        try:
            LocationRepository.rename(loc_id, new_name)
            self._load_locations()
        except Exception as e:
            QMessageBox.critical(self, tr("error.generic.title"), str(e))

    def _on_delete(self):
        loc_id = self._selected_id()
        if not loc_id:
            return

        all_locs = LocationRepository.get_all()
        item_count = LocationRepository.get_item_count(loc_id)
        loc_name = next((loc.name for loc in all_locs if loc.id == loc_id), "")

        # Check: cannot delete the only location
        if len(all_locs) <= 1:
            QMessageBox.warning(
                self, tr("error.generic.title"), tr("location.error.last_location")
            )
            return

        if item_count == 0:
            # Empty location — simple confirm
            reply = QMessageBox.question(
                self,
                tr("location.delete"),
                tr("location.delete.empty_confirm").format(name=loc_name),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
            try:
                LocationRepository.delete(loc_id)
                self._load_locations()
            except Exception as e:
                QMessageBox.critical(self, tr("error.generic.title"), str(e))
        else:
            # Location has items — offer to move to another location
            other_locs = [loc for loc in all_locs if loc.id != loc_id]
            dlg = _MoveAndDeleteDialog(loc_name, item_count, other_locs, parent=self)
            if dlg.exec() != QDialog.DialogCode.Accepted:
                return
            dest_id = dlg.get_destination_id()
            try:
                InventoryService.move_all_items_and_delete(loc_id, dest_id)
                self._load_locations()
            except Exception as e:
                QMessageBox.critical(self, tr("error.generic.title"), str(e))


class _MoveAndDeleteDialog(QDialog):
    """Dialog to choose a destination before deleting a non-empty location."""

    def __init__(
        self, loc_name: str, item_count: int, other_locations: list, parent=None
    ):
        super().__init__(parent)
        self.setWindowTitle(tr("location.delete"))
        self.setMinimumWidth(360)
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        msg = QLabel(
            tr("location.delete.has_items").format(name=loc_name, count=item_count)
        )
        msg.setWordWrap(True)
        layout.addWidget(msg)

        self.dest_combo = QComboBox()
        apply_combo_box_style(self.dest_combo)
        for loc in other_locations:
            self.dest_combo.addItem(loc.name, userData=loc.id)
        layout.addWidget(self.dest_combo)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.button(QDialogButtonBox.StandardButton.Ok).setText(
            tr("location.move_and_delete")
        )
        apply_button_style(btns.button(QDialogButtonBox.StandardButton.Ok), "danger")
        apply_button_style(
            btns.button(QDialogButtonBox.StandardButton.Cancel), "secondary"
        )
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def get_destination_id(self) -> int:
        return self.dest_combo.currentData()
