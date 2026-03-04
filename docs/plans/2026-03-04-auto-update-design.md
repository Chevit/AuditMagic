# Auto-Update Design

**Date:** 2026-03-04
**Platform:** Windows only

## Goal

When a newer GitHub release is detected on startup, the user clicks "Install Update" and the app handles the entire process: downloads the new exe, swaps files, and relaunches — no manual steps.

## Approach

Hidden PowerShell helper swap. The running exe cannot be overwritten on Windows while in use, so the app downloads the new exe to a temp filename, writes a small PowerShell script that performs the swap after the app exits, launches it hidden, then quits.

## Components

### `src/auto_updater.py` (new)

- `DownloadWorker(QThread)` — streams the new exe from `UpdateInfo.download_url` to `<exe_dir>/AuditMagic_update.exe`
  - Signals: `progress(int)` (0–100), `finished(bool)` (success/fail), `error(str)`
  - Uses `urllib.request.urlopen` with chunked reads (16 KB chunks)
  - Cleans up partial download on failure
- `launch_updater(exe_path: str, update_path: str) -> None`
  - Writes a `.ps1` script to `tempfile.mktemp(suffix=".ps1")`
  - Script body:
    ```powershell
    Start-Sleep -Seconds 2
    Move-Item -Force "<update_path>" "<exe_path>"
    Start-Process "<exe_path>"
    ```
  - Launches: `subprocess.Popen(['powershell', '-WindowStyle', 'Hidden', '-ExecutionPolicy', 'Bypass', '-File', script_path])`
- Dev-mode guard: functions raise `RuntimeError` if `not getattr(sys, 'frozen', False)`

### `src/ui/dialogs/update_dialog.py` (modified)

- Replace "Download" (opens browser) with "Install Update" button (primary)
- Keep "Skip" button
- On "Install Update" click:
  - Disable both buttons
  - Show `QProgressBar` (0–100)
  - Start `DownloadWorker`
  - Connect `progress` → progress bar update
  - Connect `finished(True)` → call `launch_updater`, then `QApplication.instance().quit()`
  - Connect `finished(False)` → show error label, re-enable buttons
- Dev-mode fallback: if `not sys.frozen`, "Install Update" opens browser (existing behavior)

### No changes to

- `update_checker.py` — already fetches `download_url` and `html_url`
- `main.py` — `UpdateCheckWorker` and `_show_update_dialog` unchanged

## Data Flow

```
startup → UpdateCheckWorker → check_for_update() → UpdateInfo
       → _show_update_dialog(info) → UpdateDialog shown

user clicks "Install Update"
       → DownloadWorker starts
       → streams exe to AuditMagic_update.exe
       → on success: launch_updater() writes + launches .ps1, app exits
       → PS1 runs hidden: waits 2s, moves update over original, relaunches
```

## Error Handling

| Scenario | Behavior |
|---|---|
| `download_url` empty | Fall back to `html_url`, open browser |
| Network error during download | Show error label, re-enable buttons, delete partial file |
| Not running as frozen exe | Browser fallback, no swap attempted |
| PowerShell unavailable | Unlikely on Win 10/11; would silently fail — no relaunch |

## Files Changed

| File | Change |
|---|---|
| `src/auto_updater.py` | New — download worker + PS launcher |
| `src/ui/dialogs/update_dialog.py` | Modified — progress bar, install flow |
