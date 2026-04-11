# Design: Defer First-Location Wizard to After Window Is Visible

**Date:** 2026-04-11
**Status:** Approved

## Problem

On a fresh install, `AuditMagic` appears frozen at the PyInstaller splash screen
showing "Loading interface...". The app is not actually frozen — the first-location
wizard dialog is open but hidden behind the splash screen.

### Root Cause

`MainWindow.__init__()` calls `_ensure_location_exists()` synchronously. On a fresh
install this immediately opens `FirstLocationDialog` via `dlg.exec()` (blocking
modal). At this point in the startup sequence:

- `window.show()` has **not** been called yet
- `_splash_close()` has **not** been called yet

So the dialog opens beneath the still-visible splash screen and the user cannot
interact with it. Alt+Tab reveals it is there, but the UX is broken.

### Startup Sequence (before fix)

```
run_migrations()
_splash("Loading interface...")
window = MainWindow()          ← __init__ → _ensure_location_exists()
                                            → FirstLocationDialog.exec()  ← HIDDEN
window.show()
_splash_close()
app.exec()
```

## Solution

Defer `_ensure_location_exists()` to the first event-loop cycle after the window
is visible. `QTimer.singleShot(0, ...)` inside a one-shot `showEvent` override
achieves this with no changes to `main.py`.

### Startup Sequence (after fix)

```
run_migrations()
_splash("Loading interface...")
window = MainWindow()          ← __init__ completes fast (no blocking dialog)
window.show()
_splash_close()
app.exec()
  └─ event loop tick 1 → _deferred_first_show()
                           → _ensure_location_exists()
                           → FirstLocationDialog.exec()  ← VISIBLE, on top of window
```

## Changes

All changes are in `src/ui/main_window.py`. `main.py` is untouched.

### 1. `__init__`: remove `_ensure_location_exists()` call, add `_shown_once` flag

Remove the call at the current step 1. Add `self._shown_once = False` alongside
`self._current_location_id = None` at the top of `__init__`.

The remaining init steps tolerate zero locations:
- `_init_current_location()` already handles an empty location list → sets
  `_current_location_id = None`
- `_load_data_from_db()` loads an empty list — correct for a fresh install

### 2. Add `showEvent` override

```python
def showEvent(self, event: QShowEvent) -> None:
    super().showEvent(event)
    if not self._shown_once:
        self._shown_once = True
        QTimer.singleShot(0, self._deferred_first_show)
```

The `_shown_once` guard ensures the deferred call fires exactly once, even if the
window is hidden and re-shown later (e.g. system tray restore).

`QTimer.singleShot(0, ...)` yields to the event loop for one cycle, which is
sufficient to guarantee `window.show()` and `_splash_close()` have both returned
before the wizard can appear.

### 3. New `_deferred_first_show()` method

```python
def _deferred_first_show(self) -> None:
    no_locations = LocationRepository.get_count() == 0
    self._ensure_location_exists()
    if no_locations:
        # First-location wizard just completed — sync location state and reload UI
        self._init_current_location()
        self.location_selector.refresh_locations()
        self.location_selector.set_current_location(self._current_location_id)
        self._load_data_from_db()
```

The `no_locations` check before calling `_ensure_location_exists()` means the
refresh block only runs on a genuine fresh install. For existing users, locations
already exist, `_ensure_location_exists()` returns immediately, and no redundant
reload occurs.

## Unchanged Behaviour

- **Existing users**: no visible change. Deferred call returns immediately.
- **Safety-net call** in `_on_delete_item` (line ~364): unchanged. That call fires
  from within the running event loop where the window is already visible, so it
  was never affected by this bug.
- **`main.py`**: no changes.

## Testing

| Scenario | Expected |
|---|---|
| Fresh install (no DB) | Splash closes, main window appears, first-location dialog immediately overlays it |
| Existing install (locations present) | No change in behaviour; startup time unaffected |
| User cancels first-location dialog | Existing "exit?" prompt still appears |
| Window hidden and re-shown (future) | Wizard does not re-trigger |
