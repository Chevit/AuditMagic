# Multi-Platform Build Design

**Date:** 2026-02-25
**Status:** Approved

## Goal

Extend the GitHub Actions release workflow to produce native binaries for macOS and Linux in addition to the existing Windows build, using GitHub-hosted runners.

## Approach

Single platform-aware `AuditMagic.spec` + icon files committed to the repo + three parallel CI jobs.

## Section 1: Icon Files

Generate two additional icon files from the existing `icon.ico` and commit them:

- `icon.png` (512×512) — Linux PyInstaller icon
- `icon.icns` — macOS PyInstaller icon (contains sizes: 16, 32, 64, 128, 256, 512)

**Tooling:** A one-time script `scripts/generate_icons.py` using:
- `Pillow` — extracts frames from `.ico`
- `icnsutil` (pip, dev dependency) — pure-Python `.icns` creation, works on Windows

Add `icnsutil` to `requirements-dev.txt`. Run script once, commit generated files.

## Section 2: AuditMagic.spec Changes

Add platform detection at the top of the spec:

```python
import sys

if sys.platform == 'darwin':
    icon_file = 'icon.icns'
elif sys.platform == 'win32':
    icon_file = 'icon.ico'
else:
    icon_file = 'icon.png'
```

Update the `EXE` block to reference `icon_file`.

Add a conditional macOS `BUNDLE` block after `EXE`:

```python
if sys.platform == 'darwin':
    app = BUNDLE(
        exe,
        name='AuditMagic.app',
        icon=icon_file,
        bundle_identifier='com.chevit.auditmagic',
    )
```

No changes needed to app Python code — `icon.ico` in `datas` is only used to set the executable icon at build time on Windows, not loaded at runtime.

## Section 3: GitHub Actions Workflow

Three parallel jobs in `.github/workflows/build.yml`, all triggered on `v*` tag push or `workflow_dispatch`.

### build-windows (unchanged)
- Runner: `self-hosted`
- Shell: `cmd`
- Output: `dist/AuditMagic.exe`

### build-macos (new)
- Runner: `macos-latest`
- Steps:
  1. `actions/setup-python@v4` (Python 3.11)
  2. Create venv, install `requirements.txt` + `pyinstaller`
  3. `pyinstaller AuditMagic.spec`
  4. `cd dist && zip -r ../AuditMagic-macOS.zip AuditMagic.app`
  5. Upload `AuditMagic-macOS.zip` to release

### build-linux (new)
- Runner: `ubuntu-latest`
- Steps:
  1. `sudo apt-get install -y libxcb-xinerama0 libxcb-cursor0`
  2. `actions/setup-python@v4` (Python 3.11)
  3. Create venv, install `requirements.txt` + `pyinstaller`
  4. `QT_QPA_PLATFORM=offscreen pyinstaller AuditMagic.spec`
  5. Rename `dist/AuditMagic` → `AuditMagic-linux`
  6. Upload `AuditMagic-linux` to release

## Release Artifacts

| Platform | File               |
|----------|--------------------|
| Windows  | `AuditMagic.exe`   |
| macOS    | `AuditMagic-macOS.zip` |
| Linux    | `AuditMagic-linux` |

All three files attached to the same GitHub Release via `softprops/action-gh-release@v2`.

## Known Limitations

- **macOS Gatekeeper**: Without code signing, users see a warning on first launch. Workaround: right-click → Open. Code signing is out of scope.
- **Linux desktop integration**: No `.desktop` file or AppImage packaging — plain binary only.
