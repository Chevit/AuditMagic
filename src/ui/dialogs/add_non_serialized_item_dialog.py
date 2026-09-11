"""Dialog for adding a new non-serialized inventory item (has a quantity)."""

from typing import Optional

from PyQt6.QtCore import QStringListModel, Qt, QTimer
from PyQt6.QtGui import QFont, QIntValidator
from PyQt6.QtWidgets import (
    QComboBox,
    QCompleter,
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from core.logger import logger
from core.repositories import LocationRepository
from core.services import InventoryService
from ui.dialogs.validation_feedback import show_validation_errors
from ui.dialogs.wrapping_text_edit import WrappingTextEdit
from ui.form_rules import add_item_rules, has_serialization_conflict
from ui.models.inventory_item import InventoryItem
from ui.styles import (
    apply_button_style,
    apply_combo_box_style,
    apply_input_style,
    apply_text_edit_style,
)
from ui.translations import tr
from ui.validators import ItemTypeValidator


class AddNonSerializedItemDialog(QDialog):
    """Dialog for adding a new non-serialized item with a quantity."""

    def __init__(self, current_location_id: Optional[int] = None, parent=None):
        super().__init__(parent)
        self._current_location_id = current_location_id
        self._result_item: Optional[InventoryItem] = None
        self._type_conflict: bool = False
        self._type_debounce_timer = QTimer(self)
        self._type_debounce_timer.setSingleShot(True)
        self._type_debounce_timer.timeout.connect(self._on_type_or_subtype_changed)
        self._setup_ui()
        self._setup_validators()
        self._setup_autocomplete()

    def _setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle(tr("dialog.add_non_serialized_item.title"))
        self.setMinimumWidth(400)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        header_label = QLabel(tr("dialog.add_non_serialized_item.header"))
        header_font = QFont()
        header_font.setPointSize(14)
        header_font.setBold(True)
        header_label.setFont(header_font)
        header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header_label)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)

        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        label_font = QFont()
        label_font.setBold(True)

        type_label = QLabel(tr("label.type"))
        type_label.setFont(label_font)
        self.type_edit = QLineEdit()
        self.type_edit.setPlaceholderText(tr("placeholder.type"))
        apply_input_style(self.type_edit)
        form_layout.addRow(type_label, self.type_edit)

        subtype_label = QLabel(tr("label.subtype"))
        self.subtype_edit = QLineEdit()
        self.subtype_edit.setPlaceholderText(tr("placeholder.subtype"))
        apply_input_style(self.subtype_edit)
        form_layout.addRow(subtype_label, self.subtype_edit)

        self.type_status_label = QLabel("")
        self.type_status_label.setWordWrap(True)
        form_layout.addRow("", self.type_status_label)

        quantity_label = QLabel(tr("label.quantity"))
        quantity_label.setFont(label_font)
        self.quantity_input = QLineEdit()
        self.quantity_input.setPlaceholderText(tr("placeholder.quantity"))
        quantity_validator = QIntValidator(1, 999999, self)
        self.quantity_input.setValidator(quantity_validator)
        apply_input_style(self.quantity_input, large=True)
        form_layout.addRow(quantity_label, self.quantity_input)

        initial_notes_label = QLabel(tr("label.initial_notes"))
        self.initial_notes_edit = WrappingTextEdit()
        self.initial_notes_edit.setPlaceholderText(tr("placeholder.initial_notes"))
        self.initial_notes_edit.setMaximumHeight(60)
        apply_text_edit_style(self.initial_notes_edit)
        form_layout.addRow(initial_notes_label, self.initial_notes_edit)

        loc_label = QLabel(tr("location.title"))
        loc_label.setFont(label_font)
        self.location_combo = QComboBox()
        apply_combo_box_style(self.location_combo)
        for loc in LocationRepository.get_all():
            self.location_combo.addItem(loc.name, userData=loc.id)
        if self._current_location_id is not None:
            for i in range(self.location_combo.count()):
                if self.location_combo.itemData(i) == self._current_location_id:
                    self.location_combo.setCurrentIndex(i)
                    break
        form_layout.addRow(loc_label, self.location_combo)

        layout.addLayout(form_layout)
        layout.addStretch()

        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_button = QPushButton(tr("button.cancel"))
        apply_button_style(cancel_button, "danger")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        add_button = QPushButton(tr("button.add"))
        apply_button_style(add_button, "primary")
        add_button.setDefault(True)
        add_button.clicked.connect(self._on_add_clicked)
        button_layout.addWidget(add_button)

        layout.addLayout(button_layout)

        self.type_edit.setFocus()

    def _setup_validators(self):
        """Set up input validators for form fields."""
        self.type_edit.setValidator(ItemTypeValidator(self))
        logger.debug("Non-serialized-add form validators configured")

    def _setup_autocomplete(self):
        """Setup autocomplete for type/subtype, filtered to non-serialized types."""
        self.type_completer = QCompleter(self)
        self.type_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.type_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.type_edit.setCompleter(self.type_completer)

        self.subtype_completer = QCompleter(self)
        self.subtype_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.subtype_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.subtype_edit.setCompleter(self.subtype_completer)

        self.type_edit.textChanged.connect(self._update_type_autocomplete)
        self.type_edit.textChanged.connect(self._update_subtype_autocomplete)

        self.type_edit.textChanged.connect(self._restart_type_debounce)
        self.subtype_edit.textChanged.connect(self._restart_type_debounce)

        logger.debug("Non-serialized-add autocomplete configured")

    def _update_type_autocomplete(self, text: str):
        """Update autocomplete suggestions for type, non-serialized types only."""
        try:
            suggestions = InventoryService.get_autocomplete_types(
                text, is_serialized=False
            )
            self.type_completer.setModel(QStringListModel(suggestions))
        except Exception as e:
            logger.error(f"Failed to load type autocomplete: {e}")

    def _update_subtype_autocomplete(self, type_text: str):
        """Update autocomplete suggestions for subtype, non-serialized types only."""
        if not type_text:
            return
        try:
            suggestions = InventoryService.get_autocomplete_subtypes(
                type_text, is_serialized=False
            )
            self.subtype_completer.setModel(QStringListModel(suggestions))
        except Exception as e:
            logger.error(f"Failed to load subtype autocomplete: {e}")

    def _restart_type_debounce(self):
        """Restart 300ms debounce timer for the type/subtype conflict lookup."""
        self._type_debounce_timer.stop()
        self._type_debounce_timer.start(300)

    def _on_type_or_subtype_changed(self):
        """Show a conflict warning or an info match for the typed Type/Subtype.

        A Serialization Conflict (existing type with a different is_serialized)
        blocks the save — see _on_add_clicked. A matching existing type is only
        informational.
        """
        type_name = self.type_edit.text().strip()
        sub_type = self.subtype_edit.text().strip()

        if not type_name:
            self.type_status_label.setText("")
            self._type_conflict = False
            return

        try:
            existing = InventoryService.get_item_type_by_name_subtype(
                type_name, sub_type
            )
        except Exception as e:
            logger.warning(f"Type lookup failed: {e}")
            return

        self._type_conflict = has_serialization_conflict(
            existing_is_serialized=existing.is_serialized if existing else None,
            current_is_serialized=False,
        )
        if self._type_conflict:
            self.type_status_label.setStyleSheet("color: #c62828; font-style: italic;")
            self.type_status_label.setText(
                tr("error.serialized_conflict").format(
                    name=type_name, state=tr("label.serialized_badge")
                )
            )
        elif existing is not None:
            self.type_status_label.setStyleSheet("font-style: italic;")
            self.type_status_label.setText(tr("message.type_exists_non_serialized"))
        else:
            self.type_status_label.setText("")

    def _on_add_clicked(self):
        """Validate and accept the dialog."""
        if self._type_conflict:
            QMessageBox.warning(
                self, tr("message.validation_error"), self.type_status_label.text()
            )
            self.type_edit.setFocus()
            return

        item_type = self.type_edit.text().strip()
        sub_type = self.subtype_edit.text().strip()
        quantity_text = self.quantity_input.text().strip()
        initial_notes = self.initial_notes_edit.toPlainText().strip()

        errors = add_item_rules(
            item_type=item_type,
            quantity_text=quantity_text,
            serial_number="",
            initial_notes=initial_notes,
            is_serialized=False,
        )
        if errors:
            show_validation_errors(
                self,
                errors,
                widgets={
                    "type": self.type_edit,
                    "quantity": self.quantity_input,
                    "notes": self.initial_notes_edit,
                },
                log_prefix="Non-serialized-add form",
            )
            return

        quantity = int(quantity_text)
        logger.info(
            f"Non-serialized-add form validation passed - creating item: "
            f"type='{item_type}', qty={quantity}"
        )
        location_id = self.location_combo.currentData()

        try:
            existing = InventoryService.find_non_serialized_at_location(
                type_name=item_type, sub_type=sub_type, location_id=location_id
            )
            if existing is not None:
                answer = QMessageBox.question(
                    self,
                    tr("dialog.add_item.merge.title"),
                    tr("dialog.add_item.merge.prompt").format(quantity=quantity),
                )
                if answer == QMessageBox.StandardButton.Yes:
                    result = InventoryService.add_quantity(
                        item_id=existing.id,
                        quantity=quantity,
                        notes=initial_notes,
                    )
                    if result is None:
                        QMessageBox.warning(
                            self,
                            tr("error.generic.title"),
                            tr("error.generic.message"),
                        )
                        logger.warning(
                            f"Merge failed: item id={existing.id} not found "
                            "during add_quantity"
                        )
                        return
                    self._result_item = result
                    logger.info(f"Merged quantity into existing item: id={existing.id}")
                    self.accept()
                else:
                    QMessageBox.information(
                        self,
                        tr("dialog.add_item.duplicate.title"),
                        tr("dialog.add_item.duplicate.message"),
                    )
                return

            self._result_item = InventoryService.create_item(
                item_type_name=item_type,
                item_sub_type=sub_type,
                quantity=quantity,
                is_serialized=False,
                location_id=location_id,
                transaction_notes=initial_notes or "",
            )
            logger.info(f"Item created successfully: id={self._result_item.id}")
            self.accept()
        except ValueError as e:
            QMessageBox.warning(self, tr("message.validation_error"), str(e))
            logger.error(f"Item creation failed with validation error: {e}")
        except Exception as e:
            QMessageBox.critical(
                self,
                tr("error.generic.title"),
                f"{tr('error.generic.message')}\n\n{str(e)}",
            )
            logger.error(f"Item creation failed: {e}", exc_info=True)

    def get_item(self) -> Optional[InventoryItem]:
        """Return the created item, or None if dialog was cancelled."""
        return self._result_item
