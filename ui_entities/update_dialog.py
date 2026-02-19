"""Update notification dialog."""

import webbrowser

from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from styles import apply_button_style
from ui_entities.translations import tr
from update_checker import UpdateInfo


class UpdateDialog(QDialog):
    """Dialog shown when a new version is available."""

    def __init__(self, update_info: UpdateInfo, parent=None):
        super().__init__(parent)
        self._update_info = update_info
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        self.setWindowTitle(tr("update.title"))
        self.setMinimumWidth(450)
        self.setMinimumHeight(250)

        layout = QVBoxLayout(self)

        # Header
        header = QLabel(tr("update.available", version=self._update_info.version))
        header.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(header)

        # Current version
        from version import __version__

        current_label = QLabel(tr("update.current_version", version=__version__))
        current_label.setStyleSheet("color: #666;")
        layout.addWidget(current_label)

        # Release notes
        if self._update_info.release_notes:
            notes_label = QLabel(tr("update.release_notes"))
            notes_label.setStyleSheet("font-weight: bold; margin-top: 8px;")
            layout.addWidget(notes_label)

            notes_text = QTextEdit()
            notes_text.setPlainText(self._update_info.release_notes)
            notes_text.setReadOnly(True)
            notes_text.setMaximumHeight(150)
            layout.addWidget(notes_text)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        skip_button = QPushButton(tr("update.skip"))
        apply_button_style(skip_button, "secondary")
        skip_button.clicked.connect(self.reject)
        button_layout.addWidget(skip_button)

        download_button = QPushButton(tr("update.download"))
        apply_button_style(download_button, "primary")
        download_button.clicked.connect(self._open_download)
        button_layout.addWidget(download_button)

        layout.addLayout(button_layout)

    def _open_download(self) -> None:
        """Open the download URL in the default browser."""
        url = self._update_info.download_url or self._update_info.html_url
        if url:
            webbrowser.open(url)
        self.accept()
