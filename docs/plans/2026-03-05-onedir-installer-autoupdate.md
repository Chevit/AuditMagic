# Onedir + Installer + Auto-Update Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Switch AuditMagic from onefile PyInstaller packaging to onedir, add an Inno Setup installer for fresh installs, and update the auto-update mechanism to download a zip and swap the folder.

**Architecture:** PyInstaller onedir produces a `dist/AuditMagic/` folder instead of a single `.exe`. CI zips that folder as `AuditMagic-update.zip` (for auto-update) and also builds an Inno Setup installer `AuditMagic-Setup.exe` (for first-time installation). The auto-updater downloads the zip, extracts it next to the install dir, then launches a hidden PowerShell script that waits for the app to exit and uses `robocopy` to swap folder contents.

**Tech Stack:** PyInstaller, Inno Setup 6, PowerShell (robocopy + Expand-Archive), Python zipfile not needed (all extraction done in PS1), GitHub Actions on self-hosted Windows runner.

---

## Task 1: Convert AuditMagic.spec from onefile to onedir

**Files:**
- Modify: `AuditMagic.spec`

**Background:** Currently `EXE` receives `a.binaries` and `a.datas` directly (onefile). In onedir mode, `EXE` only gets `a.scripts`, and a `COLLECT` step bundles everything into the output folder. No `BUNDLE` is needed (Windows only now).

**Step 1: Modify AuditMagic.spec**

Replace the current `pyz`, `exe`, and bundle sections with:

```python
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,          # <-- key difference for onedir
    name='AuditMagic',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    icon=icon_file,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AuditMagic',
)
```

Remove the `if sys.platform == "darwin": app = BUNDLE(...)` block entirely (macOS build is disabled in CI anyway).

**Step 2: Build locally to verify**

```cmd
.venv\Scripts\pyinstaller AuditMagic.spec
```

Expected: `dist\AuditMagic\` folder exists containing `AuditMagic.exe` plus many `.dll` and `_internal/` files. No single `dist\AuditMagic.exe` file.

**Step 3: Smoke test the built app**

```cmd
dist\AuditMagic\AuditMagic.exe
```

Expected: App launches normally, no crash, no DLL errors.

**Step 4: Commit**

```bash
git add AuditMagic.spec
git commit -m "build: switch PyInstaller to onedir packaging"
```

---

## Task 2: Create Inno Setup installer script

**Files:**
- Create: `installer/AuditMagic.iss`

**Background:** Inno Setup is a free Windows installer creator. Install to `{localappdata}\AuditMagic` (no UAC needed, consistent with where auto-update will write). `PrivilegesRequired=lowest` means no admin prompt.

**Step 1: Create `installer/` directory and `AuditMagic.iss`**

```ini
; AuditMagic Installer Script
; Requires Inno Setup 6: https://jrsoftware.org/isinfo.php

#define AppName "AuditMagic"
#define AppVersion "1.0.14"
#define AppPublisher "Chevit"
#define AppExeName "AuditMagic.exe"

[Setup]
AppId={{D4A3B2C1-E5F6-4789-A012-B3C4D5E6F789}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL=https://github.com/Chevit/AuditMagic
AppSupportURL=https://github.com/Chevit/AuditMagic/issues
AppUpdatesURL=https://github.com/Chevit/AuditMagic/releases
DefaultDirName={localappdata}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=dist
OutputBaseFilename=AuditMagic-Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
UninstallDisplayIcon={app}\{#AppExeName}
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\AuditMagic\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
```

**Step 2: Verify Inno Setup is installed on the self-hosted runner**

On the runner machine, check if Inno Setup is installed:
```cmd
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" /?
```

If not installed: download from https://jrsoftware.org/isdl.php and install (one-time, on the runner machine).

**Step 3: Build installer locally (if Inno Setup available)**

```cmd
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\AuditMagic.iss
```

Expected: `dist\AuditMagic-Setup.exe` created.

**Step 4: Commit**

```bash
git add installer/AuditMagic.iss
git commit -m "build: add Inno Setup installer script"
```

---

## Task 3: Update auto_updater.py for onedir zip-swap

**Files:**
- Modify: `src/auto_updater.py`

**Background:** Instead of downloading a sibling `.exe`, we now download `AuditMagic-update.zip`, which contains the full onedir folder contents. A PowerShell script extracts it to a temp dir next to the install dir, waits for the process to exit, then uses `robocopy` to swap the folder (robocopy handles locked/in-use files better than Move-Item and is available on Windows Vista+).

The install dir is `Path(sys.executable).parent` (e.g., `C:\Users\chevi\AppData\Local\AuditMagic\`).

**Step 1: Replace auto_updater.py**

```python
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
        f"Wait-Process -Id {pid} -ErrorAction SilentlyContinue\n"
        "Expand-Archive -Force -Path $zip -DestinationPath $extract\n"
        "robocopy $extract $install /E /PURGE /R:3 /W:1 /NJH /NJS /NFL /NDL | Out-Null\n"
        "Remove-Item $extract -Recurse -Force\n"
        "Remove-Item $zip -Force\n"
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
```

**Step 2: Commit**

```bash
git add src/auto_updater.py
git commit -m "feat: update auto_updater for onedir zip-swap mechanism"
```

---

## Task 4: Update update_checker.py to find zip asset

**Files:**
- Modify: `src/update_checker.py`

**Background:** Releases now ship `AuditMagic-update.zip` instead of `AuditMagic.exe`. The checker must find the zip asset.

**Step 1: Change asset detection in `check_for_update()`**

Find this block (lines 54–61):
```python
# Find the .exe asset
download_url = ""
for asset in data.get("assets", []):
    if asset["name"].lower().endswith(".exe"):
        url = asset.get("browser_download_url", "")
        if url.startswith("https://"):
            download_url = url
        break
```

Replace with:
```python
# Find the update zip asset
download_url = ""
for asset in data.get("assets", []):
    if asset["name"].lower() == "auditmagic-update.zip":
        url = asset.get("browser_download_url", "")
        if url.startswith("https://"):
            download_url = url
        break
```

**Step 2: Commit**

```bash
git add src/update_checker.py
git commit -m "feat: update_checker looks for zip asset instead of exe"
```

---

## Task 5: Update update_dialog.py to use new auto_updater API

**Files:**
- Modify: `src/ui/dialogs/update_dialog.py`

**Background:** `launch_updater` now takes 3 args (exe_path, zip_path, extract_dir). `_start_download` needs to pass the zip path. `_on_download_finished` must call the updated signature.

**Step 1: Update `_start_download` method**

Find:
```python
def _start_download(self) -> None:
    """Begin downloading the update exe."""
    from auto_updater import DownloadWorker, _get_update_path

    ...
    dest = _get_update_path(sys.executable)
    self._worker = DownloadWorker(self._update_info.download_url, dest, self)
```

Replace with:
```python
def _start_download(self) -> None:
    """Begin downloading the update zip."""
    from auto_updater import DownloadWorker, _get_update_zip_path

    ...
    dest = _get_update_zip_path(sys.executable)
    self._worker = DownloadWorker(self._update_info.download_url, dest, self)
```

**Step 2: Update `_on_download_finished` method**

Find:
```python
from auto_updater import launch_updater, _get_update_path

launch_updater(sys.executable, _get_update_path(sys.executable))
```

Replace with:
```python
from auto_updater import launch_updater, _get_update_zip_path, _get_update_extract_dir

launch_updater(
    sys.executable,
    _get_update_zip_path(sys.executable),
    _get_update_extract_dir(sys.executable),
)
```

**Step 3: Commit**

```bash
git add src/ui/dialogs/update_dialog.py
git commit -m "feat: update_dialog uses new zip-based auto_updater API"
```

---

## Task 6: Update CI (build.yml)

**Files:**
- Modify: `.github/workflows/build.yml`

**Background:** After PyInstaller builds `dist\AuditMagic\`, CI must:
1. Zip the folder contents as `AuditMagic-update.zip`
2. Build the Inno Setup installer as `AuditMagic-Setup.exe`
3. Upload both to the GitHub release

**Step 1: Add zip and installer steps to `build-windows` job**

Replace the current `build-windows` steps after `Build executable` with:

```yaml
      - name: Build executable
        run: .venv\Scripts\pyinstaller AuditMagic.spec

      - name: Create update zip
        run: powershell Compress-Archive -Path dist\AuditMagic\* -DestinationPath AuditMagic-update.zip

      - name: Build installer
        run: '"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\AuditMagic.iss'

      - name: Upload Release Assets
        if: startsWith(github.ref, 'refs/tags/')
        uses: softprops/action-gh-release@v2
        with:
          files: |
            AuditMagic-update.zip
            dist/AuditMagic-Setup.exe
          generate_release_notes: true
```

**Step 2: Commit**

```bash
git add .github/workflows/build.yml
git commit -m "ci: build onedir zip + Inno Setup installer, upload both to release"
```

---

## Task 7: Version bump and end-to-end test

**Files:**
- Modify: `src/version.py` (already 1.0.14, update if needed)
- Modify: `installer/AuditMagic.iss` (sync `AppVersion` if version changes)

**Step 1: Ensure version is consistent**

Check `src/version.py`:
```python
__version__ = "1.0.14"
```

Check `installer/AuditMagic.iss`:
```ini
#define AppVersion "1.0.14"
```

**Step 2: Tag and push to trigger CI**

```bash
git tag v1.0.14
git push && git push --tags
```

Expected: CI builds `AuditMagic-update.zip` + `AuditMagic-Setup.exe`, both appear as release assets on the GitHub release page.

**Step 3: Install via AuditMagic-Setup.exe and verify app runs**

Run the installer, launch from Start Menu or Desktop shortcut. App should open normally.

**Step 4: Smoke test auto-update flow (manual)**

Temporarily lower the installed version to simulate an update being available, or set up a test release with a higher version number.

---

## Notes

- **Inno Setup must be installed on the self-hosted runner** (one-time setup). Download from https://jrsoftware.org/isdl.php.
- **robocopy exit codes 0–7 are success** (8+ are errors). The `| Out-Null` suppresses output but not the exit code; PowerShell will continue regardless since it's a separate process.
- **Existing onefile users** will not get an auto-update notification for this release because the old code looks for `.exe` assets. They must download and install `AuditMagic-Setup.exe` manually once.
- **AppVersion in AuditMagic.iss** must be kept in sync with `version.py` manually (or via a CI sed step if desired).
- **Database and config** are stored in `%LOCALAPPDATA%\AuditMagic\` (via `core/config.py`), not in the install dir, so they survive the folder swap.
