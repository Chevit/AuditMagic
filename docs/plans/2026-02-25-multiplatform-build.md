# Multi-Platform Build Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add macOS and Linux release builds to the GitHub Actions workflow alongside the existing Windows build.

**Architecture:** A one-time Python script generates `icon.png` and `icon.icns` from `icon.ico` and commits them. `AuditMagic.spec` is made platform-aware (selects icon + adds macOS `BUNDLE`). `build.yml` gains two new jobs (`build-macos`, `build-linux`) using GitHub-hosted runners.

**Tech Stack:** PyInstaller, GitHub Actions, Pillow, icnsutil, PyQt6

---

### Task 1: Add icnsutil dev dependency and write icon generation script

**Files:**
- Modify: `requirements-dev.txt`
- Create: `scripts/generate_icons.py`

**Step 1: Add `icnsutil` to `requirements-dev.txt`**

Open `requirements-dev.txt` and add `icnsutil` after the existing entries:

```
icnsutil
```

Final file should look like:
```
# Development dependencies (pinned for reproducibility)
-r requirements.txt
pytest==8.1.1
pytest-qt==4.4.0
pytest-cov==4.1.0
pytest-mock==3.12.0
black==24.3.0
mypy==1.9.0
isort==5.13.2
flake8==7.0.0
pyinstaller
icnsutil
```

**Step 2: Install the new dependency**

```bash
.venv/Scripts/pip install icnsutil
```

Expected: installs successfully with no errors.

**Step 3: Create `scripts/` directory and write the generation script**

Create `scripts/generate_icons.py` with this exact content:

```python
#!/usr/bin/env python3
"""Generate icon.png (Linux) and icon.icns (macOS) from icon.ico.

Run once from the repo root:
    python scripts/generate_icons.py
"""

import tempfile
from pathlib import Path

from PIL import Image

import icnsutil

ROOT = Path(__file__).parent.parent
SRC = ROOT / "icon.ico"

# macOS ICNS role identifiers mapped to pixel sizes
ICNS_ROLES = [
    ("icp4", 16),
    ("icp5", 32),
    ("icp6", 64),
    ("ic07", 128),
    ("ic08", 256),
    ("ic09", 512),
]


def generate_png() -> None:
    """Save a 512×512 PNG for Linux PyInstaller builds."""
    with Image.open(SRC) as img:
        img = img.convert("RGBA")
        img = img.resize((512, 512), Image.LANCZOS)
        img.save(ROOT / "icon.png")
    print("Generated icon.png (512×512)")


def generate_icns() -> None:
    """Build a multi-size ICNS file for macOS PyInstaller builds."""
    icns = icnsutil.IcnsFile()
    with tempfile.TemporaryDirectory() as tmpdir:
        with Image.open(SRC) as img:
            img = img.convert("RGBA")
            for role, size in ICNS_ROLES:
                resized = img.resize((size, size), Image.LANCZOS)
                tmp_path = Path(tmpdir) / f"icon_{size}.png"
                resized.save(tmp_path)
                icns.add_media(role, file=str(tmp_path))
    icns.write(str(ROOT / "icon.icns"))
    print("Generated icon.icns")


if __name__ == "__main__":
    generate_png()
    generate_icns()
```

**Step 4: Run the script and verify output**

```bash
python scripts/generate_icons.py
```

Expected output:
```
Generated icon.png (512×512)
Generated icon.icns
```

Verify both files exist:
```bash
ls -lh icon.png icon.icns
```

Expected: both files present, `icon.png` ~10–200 KB, `icon.icns` ~500 KB–2 MB.

**Step 5: Commit**

```bash
git add requirements-dev.txt scripts/generate_icons.py icon.png icon.icns
git commit -m "feat: add macOS and Linux icon files"
```

---

### Task 2: Make AuditMagic.spec platform-aware

**Files:**
- Modify: `AuditMagic.spec`

**Step 1: Read the current spec**

Open `AuditMagic.spec` and read its contents before making any changes.

**Step 2: Add `sys` import and platform-aware icon selection**

At the top of `AuditMagic.spec`, after the existing imports (`import os`, `import qt_material`, `import openpyxl`), add:

```python
import sys

if sys.platform == "darwin":
    icon_file = os.path.join(SPECPATH, "icon.icns")
elif sys.platform == "win32":
    icon_file = os.path.join(SPECPATH, "icon.ico")
else:
    icon_file = os.path.join(SPECPATH, "icon.png")
```

**Step 3: Update the EXE block's `icon=` parameter**

Find the line inside the `EXE(...)` call:
```python
    icon=os.path.join(SPECPATH, 'icon.ico'),
```

Replace it with:
```python
    icon=icon_file,
```

**Step 4: Add the macOS BUNDLE block after the EXE block**

After the closing `)` of the `exe = EXE(...)` block, append:

```python

if sys.platform == "darwin":
    app = BUNDLE(
        exe,
        name="AuditMagic.app",
        icon=icon_file,
        bundle_identifier="com.chevit.auditmagic",
    )
```

**Step 5: Verify Windows build still works locally**

```bash
.venv/Scripts/pyinstaller AuditMagic.spec
```

Expected: build completes without errors, `dist/AuditMagic.exe` is produced.

**Step 6: Commit**

```bash
git add AuditMagic.spec
git commit -m "feat: make AuditMagic.spec platform-aware for macOS and Linux"
```

---

### Task 3: Update build.yml with macOS and Linux jobs

**Files:**
- Modify: `.github/workflows/build.yml`

**Step 1: Read the current workflow**

Open `.github/workflows/build.yml` and read its full contents before editing.

**Step 2: Replace the file with the three-job version**

Replace the entire contents of `.github/workflows/build.yml` with:

```yaml
name: Build & Release

on:
  workflow_dispatch:
  push:
    tags:
      - 'v*'

permissions:
  contents: write

jobs:
  build-windows:
    runs-on: self-hosted
    defaults:
      run:
        shell: cmd

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up virtual environment
        run: python -m venv .venv

      - name: Install dependencies
        run: |
          .venv\Scripts\python -m pip install --upgrade pip
          .venv\Scripts\pip install -r requirements.txt
          .venv\Scripts\pip install pyinstaller

      - name: Build executable
        run: .venv\Scripts\pyinstaller AuditMagic.spec

      - name: Upload Release Asset
        if: startsWith(github.ref, 'refs/tags/')
        uses: softprops/action-gh-release@v2
        with:
          files: dist/AuditMagic.exe
          generate_release_notes: true

  build-macos:
    runs-on: macos-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.14'

      - name: Set up virtual environment
        run: python -m venv .venv

      - name: Install dependencies
        run: |
          .venv/bin/python -m pip install --upgrade pip
          .venv/bin/pip install -r requirements.txt
          .venv/bin/pip install pyinstaller

      - name: Build app bundle
        run: .venv/bin/pyinstaller AuditMagic.spec

      - name: Zip app bundle
        run: cd dist && zip -r ../AuditMagic-macOS.zip AuditMagic.app

      - name: Upload Release Asset
        if: startsWith(github.ref, 'refs/tags/')
        uses: softprops/action-gh-release@v2
        with:
          files: AuditMagic-macOS.zip

  build-linux:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Install system dependencies
        run: sudo apt-get install -y libxcb-xinerama0 libxcb-cursor0

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.14'

      - name: Set up virtual environment
        run: python -m venv .venv

      - name: Install dependencies
        run: |
          .venv/bin/python -m pip install --upgrade pip
          .venv/bin/pip install -r requirements.txt
          .venv/bin/pip install pyinstaller

      - name: Build executable
        env:
          QT_QPA_PLATFORM: offscreen
        run: .venv/bin/pyinstaller AuditMagic.spec

      - name: Rename artifact
        run: mv dist/AuditMagic AuditMagic-linux

      - name: Upload Release Asset
        if: startsWith(github.ref, 'refs/tags/')
        uses: softprops/action-gh-release@v2
        with:
          files: AuditMagic-linux
```

**Step 3: Verify YAML is valid**

```bash
python -c "import yaml; yaml.safe_load(open('.github/workflows/build.yml')); print('YAML OK')"
```

Expected: `YAML OK` (install `pyyaml` first if needed: `.venv/Scripts/pip install pyyaml`)

**Step 4: Commit**

```bash
git add .github/workflows/build.yml
git commit -m "feat: add macOS and Linux CI build jobs"
```

---

### Task 4: Trigger a test run and verify

**Step 1: Push the branch and trigger a workflow_dispatch**

If you want to test without creating a release tag, push the branch and use the GitHub UI:

1. Go to your repo → **Actions** → **Build & Release**
2. Click **Run workflow** → select branch → **Run workflow**

**Step 2: Monitor all three jobs**

All three jobs (`build-windows`, `build-macos`, `build-linux`) should appear and run in parallel. Watch for any failures.

**Step 3: Common failure scenarios and fixes**

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| macOS: `icns file not found` | `icon.icns` not committed | Re-run `python scripts/generate_icons.py`, commit, push |
| Linux: Qt platform plugin error | Missing xcb libs | Add more `apt-get` packages: `libxcb-icccm4 libxcb-image0 libxcb-keysyms1 libxcb-randr0 libxcb-render-util0` |
| macOS: `ModuleNotFoundError` | Missing hidden import | Add to `hiddenimports` in `AuditMagic.spec` |
| Any: PyInstaller hook warning | qt-material or openpyxl discovery | Verify `datas` paths in spec still resolve correctly |

**Step 4: Verify release artifacts (tag push)**

Create a test tag to trigger a full release:

```bash
git tag v-test-multiplatform
git push origin v-test-multiplatform
```

Check the GitHub Release page — all three files should be attached:
- `AuditMagic.exe`
- `AuditMagic-macOS.zip`
- `AuditMagic-linux`

Delete the test tag afterward:

```bash
git push origin --delete v-test-multiplatform
git tag -d v-test-multiplatform
```
