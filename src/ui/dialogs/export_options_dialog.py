"""Export options dialog — choose transaction scope before exporting to Excel."""

from PyQt6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from ui.styles import apply_button_style
from ui.translations import tr


class ExportOptionsDialog(QDialog):
    """Dialog that collects export options before writing an Excel file.

    Parameters
    ----------
    location_name:
        Display name of the location being exported (or "All Locations").
    has_active_filter:
        Whether a search/filter is currently active in the inventory list.
        When False the "Filtered items only" radio button is disabled.
    """

    def __init__(self, location_name: str, has_active_filter: bool = False, parent=None):
        super().__init__(parent)
        self._has_active_filter = has_active_filter

        self.setWindowTitle(tr("export.dialog.title"))
        self.setMinimumWidth(360)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # Location label
        exporting_label = QLabel(tr("export.dialog.exporting").format(name=location_name))
        layout.addWidget(exporting_label)

        # Include transactions checkbox
        self._checkbox = QCheckBox(tr("export.dialog.include_transactions"))
        self._checkbox.setChecked(False)
        layout.addWidget(self._checkbox)

        # Indented container for radio buttons
        self._scope_container = QWidget()
        scope_layout = QVBoxLayout(self._scope_container)
        scope_layout.setContentsMargins(20, 0, 0, 0)
        scope_layout.setSpacing(4)

        self._radio_all = QRadioButton(tr("export.dialog.scope.all"))
        self._radio_all.setChecked(True)
        scope_layout.addWidget(self._radio_all)

        self._radio_filtered = QRadioButton(tr("export.dialog.scope.filtered"))
        self._radio_filtered.setEnabled(has_active_filter)
        scope_layout.addWidget(self._radio_filtered)

        # Ensure the two radios are mutually exclusive
        self._button_group = QButtonGroup(self)
        self._button_group.addButton(self._radio_all)
        self._button_group.addButton(self._radio_filtered)

        layout.addWidget(self._scope_container)

        # Scope container follows checkbox state
        self._scope_container.setEnabled(False)
        self._checkbox.toggled.connect(self._scope_container.setEnabled)

        # Button box
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        ok_text = tr("export.action").rstrip(".")
        btns.button(QDialogButtonBox.StandardButton.Ok).setText(ok_text)
        apply_button_style(btns.button(QDialogButtonBox.StandardButton.Ok), "primary")
        apply_button_style(btns.button(QDialogButtonBox.StandardButton.Cancel), "secondary")
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    # ------------------------------------------------------------------
    # Public accessors
    # ------------------------------------------------------------------

    def include_transactions(self) -> bool:
        """Return True if the user wants transactions included in the export."""
        return self._checkbox.isChecked()

    def transaction_scope(self) -> str:
        """Return the selected transaction scope.

        Returns ``"filtered"`` only when the filtered radio is checked *and*
        a filter was actually active when the dialog was opened; otherwise
        returns ``"all"``.
        """
        if self._radio_filtered.isChecked() and self._has_active_filter:
            return "filtered"
        return "all"
