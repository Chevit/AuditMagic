"""Auto-update utilities: download worker and PowerShell folder-swap launcher."""

import os
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from core.logger import logger

CHUNK_SIZE = 16 * 1024  # 16 KB


def _get_install_dir(exe_path: str) -> Path:
    """Return the directory containing the running exe."""
    return Path(exe_path).parent


def _get_update_zip_path(exe_path: str) -> str:
    """Return the sibling path used to store the downloaded update zip."""
    return str(_get_install_dir(exe_path).parent / "AuditMagic_update.zip")


def _get_update_extract_dir(exe_path: str) -> str:
    """Return the sibling path where the zip will be extracted."""
    return str(_get_install_dir(exe_path).parent / "AuditMagic_new")


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
    """Background thread that downloads the update zip and emits progress signals."""

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


def launch_updater(exe_path: str, zip_path: str, extract_dir: str) -> None:
    """Write and launch a hidden PowerShell script that swaps the install folder.

    The script:
    1. Waits for the current process to exit
    2. Expands the zip to extract_dir
    3. Uses robocopy to replace install_dir contents with extract_dir contents
    4. Cleans up the zip and temp extract dir

    The user is expected to restart the application manually.

    Must only be called when running as a frozen (PyInstaller) exe.
    Raises RuntimeError otherwise.
    """
    if not getattr(sys, "frozen", False):
        raise RuntimeError(
            "launch_updater() must only be called from a frozen exe"
        )

    pid = os.getpid()
    install_dir = str(_get_install_dir(exe_path))

    script = (
        f"$zip = '{zip_path}'\n"
        f"$extract = '{extract_dir}'\n"
        f"$install = '{install_dir}'\n"
        "$self = $MyInvocation.MyCommand.Path\n"
        f"Wait-Process -Id {pid} -ErrorAction SilentlyContinue\n"
        "Expand-Archive -Force -Path $zip -DestinationPath $extract\n"
        "robocopy $extract $install /E /PURGE /R:3 /W:1 /NJH /NJS /NFL /NDL | Out-Null\n"
        "Remove-Item $extract -Recurse -Force\n"
        "Remove-Item $zip -Force\n"
        "Remove-Item $self -Force\n"
    )

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".ps1", encoding="utf-8", delete=False
    ) as f:
        f.write(script)
        script_path = f.name

    logger.info(f"Launching updater script: {script_path}")
    subprocess.Popen(
        [
            "powershell",
            "-WindowStyle", "Hidden",
            "-ExecutionPolicy", "Bypass",
            "-File", script_path,
        ],
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
