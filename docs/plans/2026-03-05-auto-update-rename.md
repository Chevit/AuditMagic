# Auto-Update Rename Swap Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the broken PowerShell-based update swap with a reliable in-process rename approach that downloads via `requests` and leaves no leftover files next to the exe.

**Architecture:** The app downloads the new exe to `%TEMP%\AuditMagic_update.exe` using `requests`. On apply, it renames itself to `%TEMP%\AuditMagic.old.exe`, moves the update to the original path, then quits. On next startup, it silently deletes the old temp file.

**Tech Stack:** `requests` (new dep), `shutil`, `tempfile`, `os` (stdlib), PyQt6 `QThread`

---

### Task 1: Add `requests` to requirements.txt

**Files:**
- Modify: `requirements.txt`

**Step 1: Add the dependency**

Open `requirements.txt` and add this line after `openpyxl`:

```
requests==2.32.3
```

**Step 2: Install it**

```bash
pip install requests==2.32.3
```

Expected: `Successfully installed requests-2.32.3 ...`

**Step 3: Commit**

```bash
git add requirements.txt
git commit -m "feat: add requests dependency for update downloads"
```

---

### Task 2: Rewrite `auto_updater.py`

Replace the entire file. The old file used `urllib` + PowerShell. The new one uses `requests` + rename swap. No PowerShell at all.

**Files:**
- Modify: `src/auto_updater.py`

**Step 1: Replace the file contents**

```python
"""Auto-update utilities: download worker and in-process exe swap."""

import os
import shutil
import sys
import tempfile
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
    progress_callback=None,
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
        if progress_callback:
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

    def __init__(self, url: str, parent=None):
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
    shutil.move(str(_DOWNLOAD_PATH), str(exe))

    logger.info("Update applied successfully")


def cleanup_old_update() -> None:
    """Delete %TEMP%\\AuditMagic.old.exe if it exists. Silent on failure."""
    if _OLD_PATH.exists():
        try:
            _OLD_PATH.unlink()
            logger.info(f"Cleaned up old update file: {_OLD_PATH}")
        except OSError as e:
            logger.warning(f"Could not delete old update file {_OLD_PATH}: {e}")
```

**Step 2: Verify the file is valid Python**

```bash
python -c "import ast; ast.parse(open('src/auto_updater.py').read()); print('OK')"
```

Expected: `OK`

**Step 3: Commit**

```bash
git add src/auto_updater.py
git commit -m "feat: replace PowerShell swap with requests download and rename-based apply"
```

---

### Task 3: Update `update_dialog.py`

The dialog currently calls `launch_updater()` and then shows a "Restart" button that the user has to click. Now `apply_update()` does the swap synchronously, so after it succeeds we just quit.

**Files:**
- Modify: `src/ui/dialogs/update_dialog.py`

**Step 1: Update `_start_download` — remove `dest` arg from DownloadWorker**

The new `DownloadWorker` no longer takes a `dest_path` argument (it uses the constant internally). Change lines 116-117 from:

```python
dest = _get_update_path(sys.executable)
self._worker = DownloadWorker(self._update_info.download_url, dest, self)
```

to:

```python
self._worker = DownloadWorker(self._update_info.download_url, self)
```

**Step 2: Update `_on_download_finished` — replace launch_updater with apply_update + quit**

Replace the entire method body:

```python
def _on_download_finished(self, success: bool) -> None:
    """Called when download completes."""
    if not success:
        return  # _on_error already handled UI

    from auto_updater import apply_update

    try:
        apply_update(sys.executable)
    except Exception as e:
        self._on_error(str(e))
        return

    QApplication.instance().quit()
```

**Step 3: Remove now-unused imports**

Remove the `_get_update_path` and `launch_updater` references. The import at line 128 currently reads:

```python
from auto_updater import launch_updater, _get_update_path
```

This entire line is gone — replaced by the `from auto_updater import apply_update` inside `_on_download_finished`.

**Step 4: Verify the file is valid Python**

```bash
python -c "import ast; ast.parse(open('src/ui/dialogs/update_dialog.py').read()); print('OK')"
```

Expected: `OK`

**Step 5: Commit**

```bash
git add src/ui/dialogs/update_dialog.py
git commit -m "feat: apply update synchronously and quit instead of PS swap script"
```

---

### Task 4: Add startup cleanup to `main.py`

On startup, if a leftover `AuditMagic.old.exe` exists in temp (from a previous update), delete it.

**Files:**
- Modify: `src/main.py`

**Step 1: Add cleanup call inside `main()`**

Add this block right after `logger.info("AuditMagic Application Starting")` (line 48), before the `try:` block:

```python
    if getattr(sys, "frozen", False):
        from auto_updater import cleanup_old_update
        cleanup_old_update()
```

So the top of `main()` becomes:

```python
def main():
    logger.info("=" * 80)
    logger.info("AuditMagic Application Starting")
    logger.info("=" * 80)

    if getattr(sys, "frozen", False):
        from auto_updater import cleanup_old_update
        cleanup_old_update()

    try:
        app = QApplication(sys.argv)
        ...
```

**Step 2: Verify the file is valid Python**

```bash
python -c "import ast; ast.parse(open('src/main.py').read()); print('OK')"
```

Expected: `OK`

**Step 3: Verify dev mode still works**

```bash
python src/main.py
```

Expected: app launches normally; `cleanup_old_update` is not called (frozen guard), no errors.

**Step 4: Commit**

```bash
git add src/main.py
git commit -m "feat: clean up leftover .old.exe from temp on startup"
```

---

### Task 5: Manual verification (frozen build)

This task cannot be automated — it requires building the exe and observing real behavior.

**Step 1: Build**

```bash
pyinstaller AuditMagic.spec
```

Expected: `dist/AuditMagic.exe` created without errors.

**Step 2: Test happy path**

- Run `dist/AuditMagic.exe`
- If update dialog appears: click "Install Update", watch progress bar, confirm app quits
- Check `%TEMP%` for `AuditMagic.old.exe` — should exist after quit
- Re-run `dist/AuditMagic.exe` — old file should be gone

**Step 3: Test no leftover next to exe**

Confirm there is no `AuditMagic_update.exe` file in the same folder as `dist/AuditMagic.exe` at any point.

**Step 4: Commit any fixes found during testing**

```bash
git add <changed files>
git commit -m "fix: <description of fix>"
```
