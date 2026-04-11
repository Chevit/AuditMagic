# Deferred First-Location Dialog Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix a fresh-install bug where the first-location wizard is hidden behind the PyInstaller splash screen by deferring the dialog to the first event-loop cycle after the window is visible.

**Architecture:** Remove `_ensure_location_exists()` from `MainWindow.__init__()` and instead schedule it via `QTimer.singleShot(0, ...)` inside a one-shot `showEvent` override. After the wizard completes on a fresh install, re-sync location state and reload the list.

**Tech Stack:** PyQt6 (`QTimer`, `QShowEvent`, `QMainWindow`), SQLAlchemy (via `LocationRepository`)

---

### Task 1: Add imports, `_shown_once` flag, remove call from `__init__`

**Files:**
- Modify: `src/ui/main_window.py:1-17` (imports block)
- Modify: `src/ui/main_window.py:46-57` (`__init__` top)

- [ ] **Step 1: Add `QTimer` and `QShowEvent` to the PyQt6 imports**

  Open `src/ui/main_window.py`. The current `PyQt6.QtWidgets` import block is at lines 7–17. Add `QTimer` from `PyQt6.QtCore` and `QShowEvent` from `PyQt6.QtGui` alongside the existing imports:

  ```python
  from PyQt6.QtCore import QTimer
  from PyQt6.QtGui import QAction, QActionGroup, QShowEvent
  ```

  Replace the two existing lines:
  ```python
  from PyQt6.QtGui import QAction, QActionGroup
  ```
  with:
  ```python
  from PyQt6.QtCore import QTimer
  from PyQt6.QtGui import QAction, QActionGroup, QShowEvent
  ```

- [ ] **Step 2: Add `_shown_once` flag and remove `_ensure_location_exists()` from `__init__`**

  In `__init__`, the top currently reads:
  ```python
  def __init__(self):
      # _current_location_id must be set before any method that may read it
      self._current_location_id: Optional[int] = None

      super().__init__()
      uic.loadUi(resource_path("src/ui/forms/MainWindow.ui"), self)

      # Initialize database
      init_database()

      # 1. Ensure at least one location exists (shows first-launch wizard if needed)
      self._ensure_location_exists()

      # 2. Restore last-selected location from core.config (three-case sentinel logic)
      self._init_current_location()
  ```

  Change it to:
  ```python
  def __init__(self):
      # _current_location_id must be set before any method that may read it
      self._current_location_id: Optional[int] = None
      self._shown_once: bool = False

      super().__init__()
      uic.loadUi(resource_path("src/ui/forms/MainWindow.ui"), self)

      # Initialize database
      init_database()

      # 1. Restore last-selected location from core.config (three-case sentinel logic)
      # NOTE: _ensure_location_exists() is deferred to _deferred_first_show() via
      # showEvent so that the first-location wizard appears after the splash closes.
      self._init_current_location()
  ```

  The remaining steps (`_check_unassigned_items`, `_setup_ui`, etc.) are unchanged.

- [ ] **Step 3: Verify the app still starts for an existing install**

  With an existing DB (locations already present), run:
  ```
  python src/main.py
  ```
  Expected: app opens normally, inventory list loads, no visible change in behaviour.

---

### Task 2: Add `showEvent` override and `_deferred_first_show` method

**Files:**
- Modify: `src/ui/main_window.py` — add two methods after `__init__`

- [ ] **Step 1: Add `showEvent` override**

  Insert the following method immediately after `__init__` (before `_setup_ui`):

  ```python
  def showEvent(self, event: QShowEvent) -> None:
      """On first show, defer the first-location wizard to after the splash closes."""
      super().showEvent(event)
      if not self._shown_once:
          self._shown_once = True
          QTimer.singleShot(0, self._deferred_first_show)
  ```

- [ ] **Step 2: Add `_deferred_first_show` method**

  Insert immediately after `showEvent`:

  ```python
  def _deferred_first_show(self) -> None:
      """Run first-location wizard if needed, then sync location state.

      Scheduled by showEvent so this executes after window.show() and
      _splash_close() have both returned — making the wizard visible.
      Only re-syncs location state when the wizard actually ran (fresh install).
      """
      no_locations = LocationRepository.get_count() == 0
      self._ensure_location_exists()
      if no_locations:
          # Wizard just completed — sync location state and reload UI
          self._init_current_location()
          self.location_selector.refresh_locations()
          self.location_selector.set_current_location(self._current_location_id)
          self._load_data_from_db()
  ```

- [ ] **Step 3: Verify fresh-install scenario**

  Simulate a fresh install by temporarily renaming or deleting the DB file at
  `%LOCALAPPDATA%\AuditMagic\inventory.db`, then run:
  ```
  python src/main.py
  ```
  Expected:
  - Splash shows "Loading interface..." briefly
  - Main window appears (empty list)
  - Splash closes
  - **First-location dialog appears on top of the main window** (not hidden)
  - After creating a location, the main window loads correctly

  Restore the original DB file afterwards.

- [ ] **Step 4: Verify the cancel-and-exit path still works**

  Repeat the fresh-install simulation. When the first-location dialog appears,
  close it without creating a location. Expected: "A location is required. Exit?"
  prompt appears. Clicking Yes exits the app cleanly.

- [ ] **Step 5: Commit**

  ```bash
  git add src/ui/main_window.py
  git commit -m "fix: defer first-location wizard to after splash closes on fresh install"
  ```
