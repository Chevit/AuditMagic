"""Auto-update utilities: download worker and in-process exe swap."""

import os
import shutil
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path

import requests
from PyQt6.QtCore import QThread, pyqtSignal

from core.logger import logger

CHUNK_SIZE = 16 * 1024  # 16 KB

_TEMP_DIR = Path(tempfile.gettempdir())
_DOWNLOAD_PATH = _TEMP_DIR / "AuditMagic_update.exe"
_OLD_PATH = _TEMP_DIR / "AuditMagic.old.exe"


def _download_file(
    url: str,
    dest_path: Path,
    progress_callback: "Callable[[int], None] | None" = None,
) -> None:
    """Stream url to dest_path via requests, calling progress_callback(0-100).

    Raises on error. Cleans up partial file on failure.
    """
    try:
        with requests.get(
            url,
            stream=True,
            timeout=60,
            headers={"User-Agent": "AuditMagic-Updater"},
        ) as response:
            response.raise_for_status()
            total = int(response.headers.get("Content-Length", 0))
            downloaded = 0
            with open(dest_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total > 0 and progress_callback:
                            progress_callback(int(downloaded * 100 / total))
        if progress_callback and (total == 0 or downloaded < total):
            progress_callback(100)
    except Exception:
        if dest_path.exists():
            try:
                dest_path.unlink()
            except OSError:
                pass
        raise


class DownloadWorker(QThread):
    """Background thread that downloads a new exe and emits progress signals."""

    progress = pyqtSignal(int)        # 0-100
    finished = pyqtSignal(bool)       # True = success
    error_occurred = pyqtSignal(str)  # error message

    def __init__(self, url: str, parent: object | None = None):
        super().__init__(parent)
        self._url = url

    def run(self) -> None:
        try:
            _download_file(self._url, _DOWNLOAD_PATH, self.progress.emit)
            self.finished.emit(True)
        except Exception as e:
            logger.warning(f"Download failed: {e}")
            self.error_occurred.emit(str(e))
            self.finished.emit(False)


def apply_update(exe_path: str) -> None:
    """Rename running exe to %TEMP%\\AuditMagic.old.exe, move update to exe_path.

    Windows allows renaming a running exe (only deletion is blocked).
    Must only be called from a frozen (PyInstaller) exe. Raises RuntimeError otherwise.
    Raises OSError on file operation failure.
    """
    if not getattr(sys, "frozen", False):
        raise RuntimeError("apply_update() must only be called from a frozen exe")

    exe = Path(exe_path)
    logger.info(f"Applying update: renaming {exe} -> {_OLD_PATH}")
    os.rename(exe, _OLD_PATH)

    logger.info(f"Moving update: {_DOWNLOAD_PATH} -> {exe}")
    try:
        shutil.move(str(_DOWNLOAD_PATH), str(exe))
    except OSError:
        logger.error("Move failed; rolling back rename")
        try:
            os.rename(_OLD_PATH, exe)
        except OSError as rb_err:
            logger.error(f"Rollback also failed: {rb_err}")
        raise

    logger.info("Update applied successfully")


def cleanup_old_update() -> None:
    """Delete %TEMP%\\AuditMagic.old.exe if it exists. Silent on failure."""
    if _OLD_PATH.exists():
        try:
            _OLD_PATH.unlink()
            logger.info(f"Cleaned up old update file: {_OLD_PATH}")
        except OSError as e:
            logger.warning(f"Could not delete old update file {_OLD_PATH}: {e}")
