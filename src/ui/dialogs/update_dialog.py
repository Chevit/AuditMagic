"""Update notification dialog with auto-install support."""

import sys
import webbrowser

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from ui.styles import apply_button_style
from ui.translations import tr
from update_checker import UpdateInfo


class UpdateDialog(QDialog):
    """Dialog shown when a new version is available."""

    def __init__(self, update_info: UpdateInfo, parent=None):
        super().__init__(parent)
        self._update_info = update_info
        self._worker = None
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

        # Progress bar (hidden until download starts)
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.hide()
        layout.addWidget(self._progress_bar)

        # Status label (hidden until needed)
        self._status_label = QLabel()
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_label.hide()
        layout.addWidget(self._status_label)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self._skip_button = QPushButton(tr("update.skip"))
        apply_button_style(self._skip_button, "secondary")
        self._skip_button.clicked.connect(self.reject)
        button_layout.addWidget(self._skip_button)

        self._install_button = QPushButton(tr("update.install"))
        apply_button_style(self._install_button, "primary")
        self._install_button.clicked.connect(self._on_install)
        button_layout.addWidget(self._install_button)

        layout.addLayout(button_layout)

    def _on_install(self) -> None:
        """Start the install flow: download then swap, or open browser in dev mode."""
        if not getattr(sys, "frozen", False) or not self._update_info.download_url:
            # Dev mode or no direct download URL — fall back to browser
            url = self._update_info.download_url or self._update_info.html_url
            if url:
                webbrowser.open(url)
            self.accept()
            return

        self._start_download()

    def _start_download(self) -> None:
        """Begin downloading the update exe."""
        from auto_updater import DownloadWorker, _get_update_path

        self._skip_button.setEnabled(False)
        self._install_button.setEnabled(False)
        self._status_label.setText(tr("update.downloading"))
        self._status_label.setStyleSheet("")
        self._status_label.show()
        self._progress_bar.setValue(0)
        self._progress_bar.show()

        dest = _get_update_path(sys.executable)
        self._worker = DownloadWorker(self._update_info.download_url, dest, self)
        self._worker.progress.connect(self._progress_bar.setValue)
        self._worker.error_occurred.connect(self._on_error)
        self._worker.finished.connect(self._on_download_finished)
        self._worker.start()

    def _on_download_finished(self, success: bool) -> None:
        """Called when download completes."""
        if not success:
            return  # _on_error already handled UI

        from auto_updater import launch_updater, _get_update_path

        launch_updater(sys.executable, _get_update_path(sys.executable))
        QApplication.instance().quit()

    def _on_error(self, message: str) -> None:
        """Show error and re-enable buttons."""
        self._progress_bar.hide()
        self._status_label.setText(tr("update.error"))
        self._status_label.setStyleSheet("color: #c0392b;")
        self._skip_button.setEnabled(True)
        self._install_button.setEnabled(True)
