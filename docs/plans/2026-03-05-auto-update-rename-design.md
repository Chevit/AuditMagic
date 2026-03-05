# Auto-Update Rename-Based Swap Design

**Date:** 2026-03-05
**Branch:** auto_update (new branch from main)
**Replaces:** PowerShell-based `launch_updater()` approach

## Goal

Replace the broken PowerShell wait-and-swap with a reliable in-process rename approach.
Eliminate the `AuditMagic_update.exe` leftover next to the app exe.

## Approach

Windows allows renaming a running `.exe` file (only deletion is blocked).
The app moves itself to `%TEMP%` before it exits, then places the new exe at the original path.
On next startup the app deletes the leftover temp file.

## Flow

```
user clicks "Install Update"
  → DownloadWorker streams new exe → %TEMP%\AuditMagic_update.exe   (via requests)
  → on success: apply_update() runs:
      os.rename(exe_path, %TEMP%\AuditMagic.old.exe)
      shutil.move(%TEMP%\AuditMagic_update.exe, exe_path)
  → QApplication.quit()

next startup (frozen only):
  → cleanup_old_update() deletes %TEMP%\AuditMagic.old.exe if present
```

## Files Changed

| File | Change |
|---|---|
| `src/auto_updater.py` | Replace urllib + PowerShell with requests + rename swap |
| `src/ui/dialogs/update_dialog.py` | Call `apply_update()` instead of `launch_updater()` |
| `src/main.py` | Call `cleanup_old_update()` near startup |
| `requirements.txt` | Add `requests` |

## `auto_updater.py` API (new)

```python
TEMP_UPDATE = Path(tempfile.gettempdir()) / "AuditMagic_update.exe"
TEMP_OLD    = Path(tempfile.gettempdir()) / "AuditMagic.old.exe"

class DownloadWorker(QThread):
    """Uses requests.get(stream=True) instead of urllib."""
    progress = pyqtSignal(int)
    finished = pyqtSignal(bool)
    error_occurred = pyqtSignal(str)

def apply_update(exe_path: str) -> None:
    """Rename running exe to %TEMP%\AuditMagic.old.exe, move update to exe_path.
    Only call from frozen exe. Raises RuntimeError otherwise.
    Raises OSError on file operation failure.
    """

def cleanup_old_update() -> None:
    """Delete %TEMP%\AuditMagic.old.exe if it exists. Silent on failure."""
```

## Error Handling

| Scenario | Behavior |
|---|---|
| Download fails | DownloadWorker emits `error_occurred`; UI shows error, re-enables buttons |
| `apply_update()` rename fails | Raises OSError; dialog catches and shows error label |
| Not frozen | `apply_update()` raises RuntimeError; `_on_install` already guards with browser fallback |
| Leftover temp file undeletable | `cleanup_old_update()` logs warning, continues silently |

## Constraints

- Windows only (frozen exe only) — dev mode always falls back to browser
- `requests` added to `requirements.txt` (already likely transitive, but make explicit)
- No PowerShell, no background processes, no waiting
