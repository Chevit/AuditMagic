"""First step of the Add Item flow: choose serialized vs non-serialized."""

from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ui.styles import apply_button_style
from ui.translations import tr


class AddItemChooserDialog(QDialog):
    """Asks whether the new item is serialized before opening the right form."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._chose_serialized: Optional[bool] = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        self.setWindowTitle(tr("dialog.add_item_chooser.title"))
        self.setModal(True)
        self.setMinimumWidth(360)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        header_label = QLabel(tr("dialog.add_item_chooser.header"))
        header_font = QFont()
        header_font.setPointSize(14)
        header_font.setBold(True)
        header_label.setFont(header_font)
        header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_label.setWordWrap(True)
        layout.addWidget(header_label)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)

        choice_layout = QHBoxLayout()
        choice_layout.setSpacing(10)

        serialized_button = QPushButton(tr("button.add_item_chooser.with_serial"))
        apply_button_style(serialized_button, "primary")
        serialized_button.clicked.connect(self._choose_serialized)
        choice_layout.addWidget(serialized_button)

        non_serialized_button = QPushButton(
            tr("button.add_item_chooser.without_serial")
        )
        apply_button_style(non_serialized_button, "secondary")
        non_serialized_button.clicked.connect(self._choose_non_serialized)
        choice_layout.addWidget(non_serialized_button)

        layout.addLayout(choice_layout)

        cancel_layout = QHBoxLayout()
        cancel_layout.addStretch()
        cancel_button = QPushButton(tr("button.cancel"))
        apply_button_style(cancel_button, "danger")
        cancel_button.clicked.connect(self.reject)
        cancel_layout.addWidget(cancel_button)
        layout.addLayout(cancel_layout)

    def _choose_serialized(self) -> None:
        """Record the serialized choice and close."""
        self._chose_serialized = True
        self.accept()

    def _choose_non_serialized(self) -> None:
        """Record the non-serialized choice and close."""
        self._chose_serialized = False
        self.accept()

    def is_serialized_chosen(self) -> bool:
        """Return the user's choice. Only meaningful if the dialog was accepted."""
        assert self._chose_serialized is not None
        return self._chose_serialized
