# Implement Auto-Update System

Step-by-step instructions for adding PyInstaller packaging, GitHub Actions CI, and an in-app update checker to AuditMagic.

**GitHub repo:** `https://github.com/Chevit/AuditMagic`
**Target platform:** Windows only
**Update behavior:** Show dialog with download link (user downloads manually)

---

## Step 1: Create `version.py`

Create a new file `version.py` in the project root:

```python
"""Application version. Single source of truth for versioning."""

__version__ = "1.0.0"
```

This is the only place the version string lives. PyInstaller, the update checker, and the UI all read from here.

---

## Step 2: Create PyInstaller spec file

Create `AuditMagic.spec` in the project root.

### Key bundling requirements

The following data files MUST be included — the app uses them at runtime:

| Source | Purpose |
|--------|---------|
| `ui/MainWindow.ui` | Loaded by `uic.loadUi()` in `main_window.py` |
| `alembic.ini` | Used by `run_migrations()` in `db.py` |
| `alembic/` (entire directory) | Migration scripts, `env.py`, `script.py.mako` |
| `qt_material` package data | Theme XML files used by `apply_stylesheet()` |

### Spec file content

```python
# AuditMagic.spec
import os
import qt_material

qt_material_path = os.path.dirname(qt_material.__file__)

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('ui/MainWindow.ui', 'ui'),
        ('alembic.ini', '.'),
        ('alembic', 'alembic'),
        (qt_material_path, 'qt_material'),
    ],
    hiddenimports=[
        'sqlalchemy.dialects.sqlite',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='AuditMagic',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,           # windowed mode, no console
    disable_windowed_traceback=False,
    # icon='icon.ico',       # Uncomment when icon file is added
)
```

### Important: Fix resource paths for bundled mode

When PyInstaller bundles the app, files are extracted to a temp directory. The app needs to find them there instead of in the script directory.

**Add a helper function** to a new file `runtime.py` in the project root:

```python
"""Runtime helpers for PyInstaller compatibility."""

import os
import sys


def get_base_path() -> str:
    """Get the base path for resource files.
    
    When running from PyInstaller bundle, files are in sys._MEIPASS.
    When running from source, files are in the script directory.
    
    Returns:
        Base path string.
    """
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def resource_path(relative_path: str) -> str:
    """Get absolute path to a bundled resource file.
    
    Args:
        relative_path: Path relative to project root (e.g., 'ui/MainWindow.ui').
    
    Returns:
        Absolute path that works in both dev and bundled mode.
    """
    return os.path.join(get_base_path(), relative_path)
```

### Files that need `resource_path()` patching

1. **`ui_entities/main_window.py`** — wherever `uic.loadUi()` is called:
   ```python
   from runtime import resource_path
   # Change:
   uic.loadUi("ui/MainWindow.ui", self)
   # To:
   uic.loadUi(resource_path("ui/MainWindow.ui"), self)
   ```

2. **`db.py`** — in `run_migrations()`:
   ```python
   from runtime import resource_path
   # Change:
   alembic_cfg = Config(os.path.join(os.path.dirname(__file__), "alembic.ini"))
   # To:
   alembic_cfg = Config(resource_path("alembic.ini"))
   alembic_cfg.set_main_option("script_location", resource_path("alembic"))
   ```

**IMPORTANT:** Search for ANY other hardcoded file paths in the codebase that reference bundled resources and apply `resource_path()` to them too. Check `alembic/env.py` — the `sys.path.insert` line may also need adjustment. In bundled mode the parent directory of `alembic/env.py` will be inside `_MEIPASS`, so the existing logic should still work, but verify by testing the built `.exe`.

---

## Step 3: Create the Update Checker service

Create `update_checker.py` in the project root:

```python
"""GitHub release update checker for AuditMagic."""

import json
import urllib.request
import urllib.error
from dataclasses import dataclass
from typing import Optional

from logger import logger
from version import __version__

GITHUB_API_URL = "https://api.github.com/repos/Chevit/AuditMagic/releases/latest"
REQUEST_TIMEOUT = 10  # seconds


@dataclass
class UpdateInfo:
    """Information about an available update."""
    version: str
    download_url: str
    release_notes: str
    html_url: str  # GitHub release page URL


def check_for_update() -> Optional[UpdateInfo]:
    """Check GitHub for a newer release.

    Returns:
        UpdateInfo if a newer version is available, None otherwise.
    """
    try:
        logger.info(f"Checking for updates (current: {__version__})...")

        request = urllib.request.Request(
            GITHUB_API_URL,
            headers={
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "AuditMagic-UpdateChecker",
            },
        )
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
            data = json.loads(response.read().decode("utf-8"))

        latest_tag = data.get("tag_name", "")
        latest_version = latest_tag.lstrip("v")

        if not latest_version:
            logger.warning("No version tag found in latest release")
            return None

        if _is_newer(latest_version, __version__):
            # Find the .exe asset
            download_url = ""
            for asset in data.get("assets", []):
                if asset["name"].lower().endswith(".exe"):
                    download_url = asset["browser_download_url"]
                    break

            info = UpdateInfo(
                version=latest_version,
                download_url=download_url,
                release_notes=data.get("body", "") or "",
                html_url=data.get("html_url", ""),
            )
            logger.info(f"Update available: {latest_version}")
            return info

        logger.info("Application is up to date")
        return None

    except urllib.error.URLError as e:
        logger.warning(f"Network error checking for updates: {e}")
        return None
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.warning(f"Error parsing update response: {e}")
        return None
    except Exception as e:
        logger.warning(f"Unexpected error checking for updates: {e}")
        return None


def _is_newer(latest: str, current: str) -> bool:
    """Compare version strings (semantic versioning).

    Args:
        latest: Latest version string (e.g., "1.2.0").
        current: Current version string.

    Returns:
        True if latest is newer than current.
    """
    try:
        latest_parts = [int(x) for x in latest.split(".")]
        current_parts = [int(x) for x in current.split(".")]
        return latest_parts > current_parts
    except (ValueError, AttributeError):
        return False
```

**Note:** This uses `urllib` (stdlib) instead of `requests` to avoid adding a new dependency. If you prefer `requests`, add it to `requirements.txt` first.

---

## Step 4: Create the Update Dialog

Create `ui_entities/update_dialog.py`:

```python
"""Update notification dialog."""

import webbrowser

from PyQt6.QtCore import Qt
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
```

---

## Step 5: Add translation keys

Add these keys to `ui_entities/translations.py` in both `uk` and `en` dictionaries:

```python
# English
"update.title": "Update Available",
"update.available": "A new version {version} is available!",
"update.current_version": "Current version: {version}",
"update.release_notes": "Release Notes:",
"update.skip": "Skip",
"update.download": "Download",

# Ukrainian
"update.title": "Доступне оновлення",
"update.available": "Доступна нова версія {version}!",
"update.current_version": "Поточна версія: {version}",
"update.release_notes": "Примітки до випуску:",
"update.skip": "Пропустити",
"update.download": "Завантажити",
```

**Important:** Check how the existing `tr()` function handles format parameters. If it uses `.format(**kwargs)`, the `{version}` placeholders above will work. If it doesn't support kwargs, update `tr()` to accept `**kwargs` and call `.format(**kwargs)` on the result string before returning.

---

## Step 6: Integrate into `main.py`

Add the update check after the main window is shown. It should run in a background thread so it doesn't block the UI.

```python
# Add these imports at the top of main.py:
from PyQt6.QtCore import QThread, pyqtSignal
from update_checker import check_for_update, UpdateInfo
from version import __version__


# Add this worker class before main():
class UpdateCheckWorker(QThread):
    """Background thread for checking updates."""
    update_available = pyqtSignal(object)  # emits UpdateInfo

    def run(self):
        result = check_for_update()
        if result:
            self.update_available.emit(result)


# Inside main(), after window.show():
def _show_update_dialog(update_info: UpdateInfo):
    from ui_entities.update_dialog import UpdateDialog
    dialog = UpdateDialog(update_info, window)
    dialog.exec()

update_worker = UpdateCheckWorker()
update_worker.update_available.connect(_show_update_dialog)
update_worker.start()
```

Also display the current version in the main window title. In `main.py`, after creating `window`:

```python
from version import __version__
window.setWindowTitle(f"{window.windowTitle()} v{__version__}")
```

---

## Step 7: Create GitHub Actions workflow

Create the directory `.github/workflows/` and add `build.yml`:

```yaml
name: Build & Release

on:
  push:
    tags:
      - 'v*'

permissions:
  contents: write

jobs:
  build-windows:
    runs-on: windows-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pyinstaller

      - name: Build executable
        run: pyinstaller AuditMagic.spec

      - name: Upload Release Asset
        uses: softprops/action-gh-release@v2
        with:
          files: dist/AuditMagic.exe
          generate_release_notes: true
```

### How to trigger a release

1. Update `__version__` in `version.py` (e.g., `"1.1.0"`)
2. Commit: `git commit -am "Bump version to 1.1.0"`
3. Tag: `git tag v1.1.0`
4. Push: `git push && git push --tags`
5. GitHub Actions automatically builds the `.exe` and creates a release

Alternatively, create the release manually on GitHub and upload the `.exe` by hand — the update checker works either way since it reads from the Releases API.

---

## Step 8: Update `.gitignore`

The `.gitignore` already has entries for PyInstaller (`build/`, `dist/`, `*.spec`, `*.manifest`). However, we want the `.spec` file tracked. Remove or comment out the `*.spec` line:

```gitignore
# PyInstaller
#  Usually these files are written by a python script from a template
#  before PyInstaller builds the exe, so as to inject date/other infos into it.
*.manifest
# *.spec  <-- REMOVE or comment out this line
```

---

## Step 9: Update `requirements.txt`

No new dependencies needed — the update checker uses `urllib` from stdlib and `webbrowser` from stdlib.

Add `pyinstaller` to `requirements-dev.txt`:

```
pyinstaller
```

---

## Step 10: Update `CLAUDE.md`

Add to the project structure section:

```
version.py           # Single source of truth for app version
runtime.py           # PyInstaller resource path helpers
update_checker.py    # GitHub release update checker
AuditMagic.spec      # PyInstaller build specification
.github/workflows/   # GitHub Actions CI
  build.yml          # Build & release workflow
```

Add a new section:

```markdown
## Auto-Update System

### Version Management
- Version defined in `version.py` (`__version__`)
- Displayed in main window title bar
- Compared against GitHub Releases API

### Packaging (PyInstaller)
- Spec file: `AuditMagic.spec`
- Bundled data: `ui/MainWindow.ui`, `alembic/`, `alembic.ini`, `qt_material`
- Resource paths resolved via `runtime.resource_path()`
- Build: `pyinstaller AuditMagic.spec`
- Output: `dist/AuditMagic.exe`

### Update Checker
- Checks `https://api.github.com/repos/Chevit/AuditMagic/releases/latest`
- Runs in QThread on app startup (non-blocking)
- Shows dialog with download link if newer version found
- Uses `urllib` (no extra dependencies)

### Release Process
1. Update `__version__` in `version.py`
2. Commit and tag: `git tag v{version}`
3. Push tag: `git push --tags`
4. GitHub Actions builds `.exe` and creates release automatically
```

---

## Summary of new/modified files

| File | Action |
|------|--------|
| `version.py` | **CREATE** — version string |
| `runtime.py` | **CREATE** — resource path helper |
| `update_checker.py` | **CREATE** — GitHub API update checker |
| `ui_entities/update_dialog.py` | **CREATE** — update notification dialog |
| `AuditMagic.spec` | **CREATE** — PyInstaller spec |
| `.github/workflows/build.yml` | **CREATE** — GitHub Actions workflow |
| `main.py` | **MODIFY** — add update check on startup, version in title |
| `db.py` | **MODIFY** — use `resource_path()` for alembic config |
| `ui_entities/main_window.py` | **MODIFY** — use `resource_path()` for .ui file |
| `ui_entities/translations.py` | **MODIFY** — add update dialog translation keys |
| `.gitignore` | **MODIFY** — allow `.spec` file |
| `requirements-dev.txt` | **MODIFY** — add `pyinstaller` |
| `CLAUDE.md` | **MODIFY** — document auto-update system |

---

## Testing checklist

1. **Run from source** — `python main.py` should still work normally (no regressions)
2. **Update check** — set `__version__ = "0.0.1"` temporarily, run app, verify dialog appears (requires at least one GitHub release to exist)
3. **Build exe** — run `pyinstaller AuditMagic.spec`, verify `dist/AuditMagic.exe` is created
4. **Run exe** — launch `dist/AuditMagic.exe`, verify:
   - Theme loads correctly (qt-material XML files found)
   - Database migrations run (alembic files found)
   - UI loads (MainWindow.ui found)
   - Update checker runs without errors
5. **GitHub Actions** — push a `v1.0.0` tag and verify the workflow builds and creates a release
