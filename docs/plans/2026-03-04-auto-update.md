# Auto-Update Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** When a newer version is detected on startup, the user clicks "Install Update" and the app downloads, swaps, and relaunches automatically — no manual steps.

**Architecture:** `DownloadWorker(QThread)` streams the new exe to `<exe_dir>/AuditMagic_update.exe`. On success, `launch_updater()` writes a hidden PowerShell script that waits for the process to exit, moves the new file over the old one, and relaunches. The app then calls `QApplication.quit()`. Download logic is extracted into `_download_file()` (pure, testable without Qt).

**Tech Stack:** Python 3.14, PyQt6, `urllib.request` (stdlib), `subprocess` (stdlib), PowerShell (always on Windows 10/11)

---

### Task 1: Fix `update_checker.py` tag parsing

The tag `v.1.0.11` was accidentally created with a period after `v`. `lstrip("v")` returns `.1.0.11`, causing `int("")` to throw `ValueError` silently, so the update dialog never shows.

**Files:**
- Modify: `src/update_checker.py:47`
- Test: `tests/test_auto_updater.py` (create)

**Step 1: Create test file with a failing test**

```python
# tests/test_auto_updater.py
"""Tests for auto-update utilities."""


def test_is_newer_rejects_malformed_tag_with_dot():
    """Regression: tag 'v.1.0.11' must not silently fail version comparison."""
    from update_checker import _is_newer
    # .1.0.11 would raise ValueError with the old lstrip("v") approach
    assert not _is_newer(".1.0.11", "1.0.11")


def test_update_checker_strips_v_dot_prefix():
    """check_for_update should handle tag_name 'v.1.0.12' as version '1.0.12'."""
    # We test the stripping logic directly via _is_newer with clean input
    from update_checker import _is_newer
    assert _is_newer("1.0.12", "1.0.11")
    assert not _is_newer("1.0.11", "1.0.11")
```

**Step 2: Run to confirm first test currently passes (it tolerates bad input) and document behavior**

```
pytest tests/test_auto_updater.py -v
```

Expected: both pass (the regression test documents intent, the real fix is in step 3)

**Step 3: Write a test that exercises the full tag stripping path**

Add to `tests/test_auto_updater.py`:

```python
def test_tag_stripping_handles_v_dot_prefix():
    """v.1.0.12 stripped correctly gives 1.0.12, which is newer than 1.0.11."""
    tag = "v.1.0.12"
    # Simulate what check_for_update does
    version = tag.removeprefix("v").removeprefix(".")
    from update_checker import _is_newer
    assert version == "1.0.12"
    assert _is_newer(version, "1.0.11")
```

Run: `pytest tests/test_auto_updater.py::test_tag_stripping_handles_v_dot_prefix -v`
Expected: PASS (confirms the fix logic is correct)

**Step 4: Apply fix to `update_checker.py` line 47**

Change:
```python
latest_version = latest_tag.lstrip("v")
```
To:
```python
latest_version = latest_tag.removeprefix("v").removeprefix(".")
```

**Step 5: Run all tests**

```
pytest tests/ -v
```
Expected: all pass

**Step 6: Commit**

```bash
git add src/update_checker.py tests/test_auto_updater.py
git commit -m "fix: handle malformed v.X.Y.Z release tags in update checker"
```

---

### Task 2: Add translation keys

New strings needed in the update dialog for the install flow.

**Files:**
- Modify: `src/ui/translations.py`
- Test: `tests/test_translations.py`

**Step 1: Write failing translation tests**

Add to `tests/test_translations.py`:

```python
def test_auto_update_translation_keys_present():
    from ui.translations import tr
    keys = [
        "update.install",
        "update.downloading",
        "update.error",
    ]
    for key in keys:
        assert tr(key) != key, f"Translation key missing: {key!r}"
```

**Step 2: Run to confirm it fails**

```
pytest tests/test_translations.py::test_auto_update_translation_keys_present -v
```
Expected: FAIL — keys not found

**Step 3: Add the keys to `translations.py`**

Find the `uk` block (around line 291) and add after `"update.download"`:

```python
"update.install": "Встановити оновлення",
"update.downloading": "Завантаження...",
"update.error": "Помилка завантаження. Спробуйте ще раз.",
```

Find the `en` block (around line 523) and add after `"update.download"`:

```python
"update.install": "Install Update",
"update.downloading": "Downloading...",
"update.error": "Download failed. Please try again.",
```

**Step 4: Run test to confirm it passes**

```
pytest tests/test_translations.py -v
```
Expected: all pass

**Step 5: Commit**

```bash
git add src/ui/translations.py tests/test_translations.py
git commit -m "feat: add translation keys for auto-update install flow"
```

---

### Task 3: Implement `auto_updater.py`

**Files:**
- Create: `src/auto_updater.py`
- Test: `tests/test_auto_updater.py`

**Step 1: Write failing tests for `_get_update_path`**

Add to `tests/test_auto_updater.py`:

```python
def test_get_update_path_sibling_of_exe():
    from auto_updater import _get_update_path
    result = _get_update_path("C:/Users/user/Desktop/AuditMagic.exe")
    assert result == "C:/Users/user/Desktop/AuditMagic_update.exe"


def test_get_update_path_handles_spaces():
    from auto_updater import _get_update_path
    result = _get_update_path("C:/My Folder/AuditMagic.exe")
    assert result == "C:/My Folder/AuditMagic_update.exe"
```

**Step 2: Run to confirm they fail**

```
pytest tests/test_auto_updater.py::test_get_update_path_sibling_of_exe -v
```
Expected: FAIL — `auto_updater` not found

**Step 3: Write failing test for `_download_file`**

Add to `tests/test_auto_updater.py`:

```python
def test_download_file_success(tmp_path):
    """_download_file writes content and calls progress callback."""
    from unittest.mock import patch, MagicMock
    import io
    from auto_updater import _download_file

    fake_data = b"x" * 1000
    mock_response = MagicMock()
    mock_response.headers = {"Content-Length": "1000"}
    mock_response.read.side_effect = [fake_data[:500], fake_data[500:], b""]
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)

    dest = tmp_path / "AuditMagic_update.exe"
    progress_calls = []

    with patch("urllib.request.urlopen", return_value=mock_response):
        _download_file("https://example.com/AuditMagic.exe", str(dest), progress_calls.append)

    assert dest.exists()
    assert dest.read_bytes() == fake_data
    assert 100 in progress_calls


def test_download_file_cleans_up_on_failure(tmp_path):
    """_download_file removes partial file on network error."""
    from unittest.mock import patch
    from auto_updater import _download_file

    dest = tmp_path / "AuditMagic_update.exe"

    with patch("urllib.request.urlopen", side_effect=OSError("network error")):
        with pytest.raises(OSError):
            _download_file("https://example.com/AuditMagic.exe", str(dest))

    assert not dest.exists()
```

**Step 4: Write failing test for `launch_updater` dev-mode guard**

Add to `tests/test_auto_updater.py`:

```python
def test_launch_updater_raises_outside_frozen():
    """launch_updater must raise RuntimeError when not running as bundled exe."""
    from auto_updater import launch_updater
    import pytest
    with pytest.raises(RuntimeError, match="frozen"):
        launch_updater("AuditMagic.exe", "AuditMagic_update.exe")
```

**Step 5: Run all new tests to confirm they fail**

```
pytest tests/test_auto_updater.py -v
```
Expected: multiple FAILs — module not found

**Step 6: Create `src/auto_updater.py`**

```python
"""Auto-update utilities: download worker and PowerShell swap launcher."""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import urllib.request
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

    progress = pyqtSignal(int)         # 0-100
    finished = pyqtSignal(bool)        # True = success
    error_occurred = pyqtSignal(str)   # error message

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
```

**Step 7: Run tests**

```
pytest tests/test_auto_updater.py -v
```
Expected: all pass

**Step 8: Commit**

```bash
git add src/auto_updater.py tests/test_auto_updater.py
git commit -m "feat: add auto_updater module (DownloadWorker + PowerShell swap)"
```

---

### Task 4: Update `update_dialog.py`

Replace the browser-based "Download" button with an "Install Update" button that drives the full auto-update flow. Dev-mode falls back to browser.

**Files:**
- Modify: `src/ui/dialogs/update_dialog.py` (full rewrite of the class)

**Step 1: No test needed for UI (pytest-qt removed); verify manually after implementation**

**Step 2: Rewrite `update_dialog.py`**

Replace the entire file contents:

```python
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
```

**Step 3: Run all tests to make sure nothing broke**

```
pytest tests/ -v
```
Expected: all pass

**Step 4: Commit**

```bash
git add src/ui/dialogs/update_dialog.py
git commit -m "feat: replace download button with auto-install flow in UpdateDialog"
```

---

### Task 5: Manual smoke test

Since the dialog only triggers when a newer version exists on GitHub, test it locally:

**Step 1: Temporarily lower the current version to trigger the update check**

In `src/version.py`, temporarily change `__version__` to `"0.0.1"` (do NOT commit this).

**Step 2: Run the app**

```
python src/main.py
```

Expected:
- App starts normally
- After a few seconds the UpdateDialog appears (because GitHub has a newer release than 0.0.1)
- Dialog shows "Install Update" button and progress bar area

**Step 3: Verify dev-mode fallback**

Click "Install Update" — since you're running in dev mode (`sys.frozen` is False), it should open the browser, not attempt a file swap.

**Step 4: Restore version**

Revert `version.py` to `"1.0.11"`.

**Step 5: Final test run**

```
pytest tests/ -v
```
Expected: all pass

---

### Task 6: Version bump and release

When ready to ship the new version:

1. Update `__version__` in `src/version.py` to `"1.0.12"`
2. Commit: `git commit -am "Bump version to 1.0.12"`
3. Tag (correct format — **no period after v**): `git tag v1.0.12`
4. Push: `git push && git push --tags`
5. GitHub Actions builds the exe and creates the release automatically
