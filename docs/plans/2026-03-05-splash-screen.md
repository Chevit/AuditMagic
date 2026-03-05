# Splash Screen Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a PyInstaller native splash screen that shows the app icon with staged loading text and version number while the app initializes.

**Architecture:** A one-time extraction script pulls the largest frame from `icon.ico` and saves `splash.png` (committed). The spec file adds a `Splash` object referencing it. `src/main.py` calls `pyi_splash.update_text()` at each loading stage and `pyi_splash.close()` after the window is shown. All `pyi_splash` calls are guarded so dev mode (`python src/main.py`) is unaffected.

**Tech Stack:** PyInstaller `Splash`, `pyi_splash` runtime module, Pillow (already in `requirements-dev.txt`)

---

### Task 1: Extract splash image from icon.ico

**Files:**
- Create: `scripts/extract_splash.py`

**Step 1: Create the extraction script**

```python
#!/usr/bin/env python
"""Extract the largest frame from icon.ico and save as splash.png."""
import sys
from pathlib import Path
from PIL import Image

root = Path(__file__).parent.parent
ico_path = root / "icon.ico"
out_path = root / "splash.png"

img = Image.open(ico_path)
# ICO files contain multiple sizes; find the largest by pixel area
sizes = img.ico.sizes()
largest = max(sizes, key=lambda s: s[0] * s[1])
img.ico.getimage(largest).save(out_path, "PNG")
print(f"Saved {largest[0]}x{largest[1]} frame to {out_path}")
```

**Step 2: Run the script**

```bash
python scripts/extract_splash.py
```

Expected output: `Saved 256x256 frame to .../splash.png` (size may vary)

**Step 3: Verify the file exists and looks correct**

Open `splash.png` in any image viewer and confirm it's the app icon at high resolution.

**Step 4: Commit**

```bash
git add scripts/extract_splash.py splash.png
git commit -m "feat: add splash image extracted from icon.ico"
```

---

### Task 2: Add pyi_splash helper to main.py

**Files:**
- Modify: `src/main.py`

**Step 1: Add the helper function after the imports in `main.py`**

Add this block right after all the `import` statements, before the `UpdateCheckWorker` class:

```python
try:
    import pyi_splash as _pyi_splash  # only available in PyInstaller bundle

    def _splash(text: str) -> None:
        _pyi_splash.update_text(text)

    def _splash_close() -> None:
        _pyi_splash.close()

except ImportError:
    def _splash(text: str) -> None:  # type: ignore[misc]
        pass

    def _splash_close() -> None:  # type: ignore[misc]
        pass
```

**Step 2: Add staged text calls inside `main()`**

The existing `main()` function currently has this sequence (approximate):
```
app = QApplication(...)
theme_manager = init_theme_manager(app)
...
run_migrations()
window = MainWindow()
window.show()
```

Modify it to:
```python
def main():
    ...
    app = QApplication(sys.argv)
    _splash(f"AuditMagic v{__version__}")   # <-- add after QApplication created
    ...
    theme_manager = init_theme_manager(app)
    ...
    _splash("Applying migrations...")        # <-- add before run_migrations()
    run_migrations()
    logger.info("Database migrations applied")

    _splash("Loading interface...")          # <-- add before MainWindow()
    window = MainWindow()
    ...
    window.show()
    _splash_close()                          # <-- add after window.show()
    logger.info("MainWindow displayed")
    ...
```

Do NOT move any existing code — only insert the four `_splash`/`_splash_close` calls in the correct positions.

**Step 3: Verify dev mode still works**

```bash
python src/main.py
```

Expected: app launches normally with no errors. The `_splash` calls are no-ops outside a PyInstaller bundle.

**Step 4: Commit**

```bash
git add src/main.py
git commit -m "feat: add pyi_splash staged loading text to main.py"
```

---

### Task 3: Update AuditMagic.spec to include Splash

**Files:**
- Modify: `AuditMagic.spec`

**Step 1: Add the `Splash` object after the `pyz = PYZ(...)` line**

After the existing line:
```python
pyz = PYZ(a.pure)
```

Add:
```python
splash = Splash(
    'splash.png',
    binaries=a.binaries,
    datas=a.datas,
    text_pos=(10, 240),
    text_size=11,
    text_color='white',
    minify_script=True,
)
```

Note: `text_pos` places text near the bottom of a 256×256 image. If the extracted image has a different height, adjust `text_pos[1]` to be `image_height - 16`. `text_color='white'` assumes a dark icon background — change to `'black'` if the icon background is light.

**Step 2: Update `EXE(...)` to include splash artifacts**

The current `EXE` call starts with:
```python
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    ...
```

Change it to:
```python
exe = EXE(
    pyz,
    a.scripts,
    splash,
    splash.binaries,
    a.binaries,
    a.datas,
    ...
```

`splash` must come before `a.binaries` and `a.datas`.

**Step 3: Verify the spec is valid Python**

```bash
python -c "exec(open('AuditMagic.spec').read())"
```

This will fail with `NameError: name 'Analysis' is not defined` — that's fine and expected (spec DSL requires PyInstaller context). What matters is no `SyntaxError`.

**Step 4: Commit**

```bash
git add AuditMagic.spec
git commit -m "feat: add PyInstaller Splash to spec"
```

---

### Task 4: Build and verify splash screen appears

**Step 1: Build the executable**

```bash
pyinstaller AuditMagic.spec
```

Expected: build completes without errors. Output: `dist/AuditMagic.exe`

**Step 2: Run the built executable**

```bash
dist/AuditMagic.exe
```

Expected:
- Splash screen appears immediately showing the icon
- Text at the bottom cycles through:
  1. `"AuditMagic v{version}"`
  2. `"Applying migrations..."`
  3. `"Loading interface..."`
- Splash closes and main window appears

**Step 3: If text is not visible**, adjust `text_color` in the spec (`'black'` vs `'white'`) and/or `text_pos` y-coordinate. Rebuild and re-test.

**Step 4: Commit any adjustments**

```bash
git add AuditMagic.spec
git commit -m "fix: adjust splash text color/position"
```
