"""Auto-update utilities: download worker and PowerShell swap launcher."""

import os
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from core.logger import logger

CHUNK_SIZE = 16 * 1024  # 16 KB


def _get_update_path(exe_path: str) -> str:
    """Return the sibling path used to store the downloaded update."""
    return str(Path(exe_path).parent / "AuditMagic_update.exe")


def _download_file(
    url: str,
    dest_path: str,
    progress_callback=None,
) -> None:
    """Stream url to dest_path, calling progress_callback(0-100) as it downloads.

    Raises on error. Cleans up a partial dest_path file on failure.
    """
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "AuditMagic-Updater"},
        )
        with urllib.request.urlopen(req, timeout=60) as response:
            total = int(response.headers.get("Content-Length", 0))
            downloaded = 0
            with open(dest_path, "wb") as f:
                while True:
                    chunk = response.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total > 0 and progress_callback:
                        progress_callback(int(downloaded * 100 / total))
        if progress_callback:
            progress_callback(100)
    except Exception:
        if os.path.exists(dest_path):
            try:
                os.remove(dest_path)
            except OSError:
                pass
        raise


class DownloadWorker(QThread):
    """Background thread that downloads a new exe and emits progress signals."""

    progress = pyqtSignal(int)        # 0-100
    finished = pyqtSignal(bool)       # True = success
    error_occurred = pyqtSignal(str)  # error message

    def __init__(self, url: str, dest_path: str, parent=None):
        super().__init__(parent)
        self._url = url
        self._dest_path = dest_path

    def run(self) -> None:
        try:
            _download_file(self._url, self._dest_path, self.progress.emit)
            self.finished.emit(True)
        except Exception as e:
            logger.warning(f"Download failed: {e}")
            self.error_occurred.emit(str(e))
            self.finished.emit(False)


def launch_updater(exe_path: str, update_path: str) -> None:
    """Write and launch a hidden PowerShell script that swaps and relaunches.

    Must only be called when running as a frozen (PyInstaller) exe.
    Raises RuntimeError otherwise.
    """
    if not getattr(sys, "frozen", False):
        raise RuntimeError(
            "launch_updater() must only be called from a frozen exe"
        )

    script = (
        f"$src = '{update_path}'\n"
        f"$dst = '{exe_path}'\n"
        "Start-Sleep -Seconds 2\n"
        "Move-Item -Force $src $dst\n"
        "Start-Process $dst\n"
    )

    script_path = tempfile.mktemp(suffix=".ps1")
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(script)

    logger.info(f"Launching updater script: {script_path}")
    subprocess.Popen(
        [
            "powershell",
            "-WindowStyle", "Hidden",
            "-ExecutionPolicy", "Bypass",
            "-File", script_path,
        ],
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
