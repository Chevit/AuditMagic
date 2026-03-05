# Splash Screen Design

**Date:** 2026-03-05
**Branch:** spalsh_screen

## Goal

Add a PyInstaller native splash screen to AuditMagic that displays while the app loads, showing staged loading text and the version number.

## Approach

Use PyInstaller's built-in `Splash` feature. The splash image is extracted once from `icon.ico` (largest resolution frame) using Pillow, committed as `splash.png`, and referenced in the spec file. The Python app uses `pyi_splash` to update text at key loading stages.

## Files

### New
- `scripts/extract_splash.py` — one-time script to extract largest ICO frame → `splash.png`
- `splash.png` — committed extracted image, used by PyInstaller at build time

### Modified
- `AuditMagic.spec` — add `Splash` object, add to `EXE`
- `src/main.py` — add staged `pyi_splash.update_text()` calls and `pyi_splash.close()`

## Spec Changes

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

Add to `EXE`: `splash, splash.binaries` before `a.binaries`.

## Loading Stages (main.py)

| Point in startup        | Text shown                      |
|-------------------------|---------------------------------|
| App starts              | `"AuditMagic v{__version__}"`   |
| Before `run_migrations` | `"Applying migrations..."`      |
| Before `MainWindow()`   | `"Loading interface..."`        |
| After `window.show()`   | `pyi_splash.close()`            |

All `pyi_splash` calls wrapped in `try/except ImportError` — dev mode unaffected.

## Constraints

- `pyi_splash` module only exists when running as a PyInstaller bundle; dev mode must not break
- `splash.png` is used by PyInstaller at build time only — not bundled as a data file
- Pillow is already in `requirements-dev.txt`
