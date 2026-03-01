# src/ Project Restructure Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Reorganize all Python source files from the flat root layout into `src/core/` and `src/ui/{dialogs,widgets,models}/` without changing any behavior.

**Architecture:** Pure folder move — no packaging, no `__init__.py` logic beyond empty markers. Python finds modules because `python src/main.py` adds `src/` to `sys.path` automatically. All imports become absolute from `src/` (e.g. `from core.models import Item`). `runtime.py` moves to `src/` and its `get_base_path()` is adjusted to return the project root (two levels up), keeping all existing `resource_path()` call-sites unchanged except the one `.ui` file path.

**Tech Stack:** Python 3.11, PyQt6, SQLAlchemy, Alembic, PyInstaller, pytest, git

---

## Important: How to Run the App After This Restructure

```bash
python src/main.py          # development
pyinstaller AuditMagic.spec # build
pytest                       # tests
alembic upgrade head         # migrations (still from project root)
```

---

### Task 1: Create New Directory Structure

**Files:**
- Create: `src/core/__init__.py`
- Create: `src/ui/__init__.py`
- Create: `src/ui/dialogs/__init__.py`
- Create: `src/ui/widgets/__init__.py`
- Create: `src/ui/models/__init__.py`

**Step 1: Create all directories and empty `__init__.py` markers**

```bash
mkdir -p src/core src/ui/forms src/ui/dialogs src/ui/widgets src/ui/models
touch src/__init__.py src/core/__init__.py src/ui/__init__.py
touch src/ui/dialogs/__init__.py src/ui/widgets/__init__.py src/ui/models/__init__.py
```

**Step 2: Verify**

```bash
find src -name "__init__.py"
```
Expected output: 6 lines, one per package dir.

**Step 3: Commit**

```bash
git add src/
git commit -m "chore: scaffold src/ directory structure"
```

---

### Task 2: Move Core Backend Files

**Files:**
- Move: `config.py` → `src/core/config.py`
- Move: `db.py` → `src/core/db.py`
- Move: `export_service.py` → `src/core/export_service.py`
- Move: `logger.py` → `src/core/logger.py`
- Move: `models.py` → `src/core/models.py`
- Move: `repositories.py` → `src/core/repositories.py`
- Move: `services.py` → `src/core/services.py`

**Step 1: Move files using git mv (git tracks these as renames)**

```bash
git mv config.py src/core/config.py
git mv db.py src/core/db.py
git mv export_service.py src/core/export_service.py
git mv logger.py src/core/logger.py
git mv models.py src/core/models.py
git mv repositories.py src/core/repositories.py
git mv services.py src/core/services.py
```

**Step 2: Verify git sees renames**

```bash
git status
```
Expected: 7 "renamed:" entries, no "deleted:".

**Step 3: Commit**

```bash
git commit -m "chore: move core backend files to src/core/"
```

---

### Task 3: Move UI Root Files

These are currently at the project root (not in `ui_entities/`).

**Files:**
- Move: `styles.py` → `src/ui/styles.py`
- Move: `theme_config.py` → `src/ui/theme_config.py`
- Move: `theme_manager.py` → `src/ui/theme_manager.py`
- Move: `validators.py` → `src/ui/validators.py`

**Step 1: Move**

```bash
git mv styles.py src/ui/styles.py
git mv theme_config.py src/ui/theme_config.py
git mv theme_manager.py src/ui/theme_manager.py
git mv validators.py src/ui/validators.py
```

**Step 2: Commit**

```bash
git commit -m "chore: move UI root files to src/ui/"
```

---

### Task 4: Move ui_entities/ Dialogs

**Files to move from `ui_entities/` → `src/ui/dialogs/`:**
add_item_dialog.py, add_serial_number_dialog.py, all_transactions_dialog.py,
edit_item_dialog.py, export_options_dialog.py, first_location_dialog.py,
item_details_dialog.py, location_management_dialog.py, quantity_dialog.py,
remove_serial_number_dialog.py, transactions_dialog.py, transfer_dialog.py,
update_dialog.py

**Step 1: Move all dialog files**

```bash
git mv ui_entities/add_item_dialog.py src/ui/dialogs/add_item_dialog.py
git mv ui_entities/add_serial_number_dialog.py src/ui/dialogs/add_serial_number_dialog.py
git mv ui_entities/all_transactions_dialog.py src/ui/dialogs/all_transactions_dialog.py
git mv ui_entities/edit_item_dialog.py src/ui/dialogs/edit_item_dialog.py
git mv ui_entities/export_options_dialog.py src/ui/dialogs/export_options_dialog.py
git mv ui_entities/first_location_dialog.py src/ui/dialogs/first_location_dialog.py
git mv ui_entities/item_details_dialog.py src/ui/dialogs/item_details_dialog.py
git mv ui_entities/location_management_dialog.py src/ui/dialogs/location_management_dialog.py
git mv ui_entities/quantity_dialog.py src/ui/dialogs/quantity_dialog.py
git mv ui_entities/remove_serial_number_dialog.py src/ui/dialogs/remove_serial_number_dialog.py
git mv ui_entities/transactions_dialog.py src/ui/dialogs/transactions_dialog.py
git mv ui_entities/transfer_dialog.py src/ui/dialogs/transfer_dialog.py
git mv ui_entities/update_dialog.py src/ui/dialogs/update_dialog.py
```

**Step 2: Commit**

```bash
git commit -m "chore: move dialog files to src/ui/dialogs/"
```

---

### Task 5: Move ui_entities/ Widgets and Models

**Files:**
- `ui_entities/inventory_delegate.py` → `src/ui/widgets/`
- `ui_entities/inventory_list_view.py` → `src/ui/widgets/`
- `ui_entities/location_selector.py` → `src/ui/widgets/`
- `ui_entities/search_widget.py` → `src/ui/widgets/`
- `ui_entities/inventory_model.py` → `src/ui/models/`
- `ui_entities/inventory_item.py` → `src/ui/models/`

**Step 1: Move**

```bash
git mv ui_entities/inventory_delegate.py src/ui/widgets/inventory_delegate.py
git mv ui_entities/inventory_list_view.py src/ui/widgets/inventory_list_view.py
git mv ui_entities/location_selector.py src/ui/widgets/location_selector.py
git mv ui_entities/search_widget.py src/ui/widgets/search_widget.py
git mv ui_entities/inventory_model.py src/ui/models/inventory_model.py
git mv ui_entities/inventory_item.py src/ui/models/inventory_item.py
```

**Step 2: Commit**

```bash
git commit -m "chore: move widget and model files to src/ui/widgets/ and src/ui/models/"
```

---

### Task 6: Move Remaining ui_entities/ Files and App Root Files

**Files:**
- `ui_entities/main_window.py` → `src/ui/main_window.py`
- `ui_entities/translations.py` → `src/ui/translations.py`
- `main.py` → `src/main.py`
- `version.py` → `src/version.py`
- `runtime.py` → `src/runtime.py`
- `update_checker.py` → `src/update_checker.py`
- `ui/MainWindow.ui` → `src/ui/forms/MainWindow.ui`

**Step 1: Move**

```bash
git mv ui_entities/main_window.py src/ui/main_window.py
git mv ui_entities/translations.py src/ui/translations.py
git mv main.py src/main.py
git mv version.py src/version.py
git mv runtime.py src/runtime.py
git mv update_checker.py src/update_checker.py
git mv ui/MainWindow.ui src/ui/forms/MainWindow.ui
```

**Step 2: Check nothing remains in ui_entities/ or ui/**

```bash
ls ui_entities/ 2>/dev/null || echo "ui_entities empty or gone"
ls ui/ 2>/dev/null || echo "ui empty or gone"
```

Expected: both should be empty (or not exist).

**Step 3: Remove now-empty directories**

```bash
rmdir ui_entities ui 2>/dev/null || true
```

**Step 4: Commit**

```bash
git commit -m "chore: move remaining files to src/, remove empty old directories"
```

---

### Task 7: Update All Imports — Run Replacement Script

All source files still have old-style imports (`from models import`, `from ui_entities.x import`, etc.). Run this Python script from the project root to fix them all at once.

**Step 1: Create the replacement script**

Create file `scripts/fix_imports.py`:

```python
"""One-time script to update imports after src/ restructure."""
import os
import re

# Map: old import prefix → new import prefix
# Order matters: more specific patterns first
REPLACEMENTS = [
    # ui_entities submodules → new subdirectories
    (r"from ui_entities\.inventory_list_view\b", "from ui.widgets.inventory_list_view"),
    (r"from ui_entities\.inventory_delegate\b", "from ui.widgets.inventory_delegate"),
    (r"from ui_entities\.inventory_model\b", "from ui.models.inventory_model"),
    (r"from ui_entities\.inventory_item\b", "from ui.models.inventory_item"),
    (r"from ui_entities\.location_selector\b", "from ui.widgets.location_selector"),
    (r"from ui_entities\.search_widget\b", "from ui.widgets.search_widget"),
    (r"from ui_entities\.main_window\b", "from ui.main_window"),
    (r"from ui_entities\.translations\b", "from ui.translations"),
    # All remaining ui_entities.* → ui.dialogs.*
    (r"from ui_entities\.", "from ui.dialogs."),
    # Core backend
    (r"from models\b", "from core.models"),
    (r"from services\b", "from core.services"),
    (r"from repositories\b", "from core.repositories"),
    (r"from db\b", "from core.db"),
    (r"from config\b", "from core.config"),
    (r"from logger\b", "from core.logger"),
    (r"from export_service\b", "from core.export_service"),
    # UI helpers (were at root, now in src/ui/)
    (r"from styles\b", "from ui.styles"),
    (r"from theme_config\b", "from ui.theme_config"),
    (r"from theme_manager\b", "from ui.theme_manager"),
    (r"from translations\b", "from ui.translations"),
    (r"from validators\b", "from ui.validators"),
]

SEARCH_DIRS = ["src", "tests", "alembic"]
EXTENSIONS = {".py"}

def fix_file(path: str) -> bool:
    with open(path, encoding="utf-8") as f:
        original = f.read()
    updated = original
    for pattern, replacement in REPLACEMENTS:
        updated = re.sub(pattern, replacement, updated)
    if updated != original:
        with open(path, "w", encoding="utf-8") as f:
            f.write(updated)
        print(f"  Updated: {path}")
        return True
    return False

changed = []
for search_dir in SEARCH_DIRS:
    for root, _, files in os.walk(search_dir):
        for fname in files:
            if os.path.splitext(fname)[1] in EXTENSIONS:
                fpath = os.path.join(root, fname)
                if fix_file(fpath):
                    changed.append(fpath)

print(f"\nDone. {len(changed)} files updated.")
```

**Step 2: Run it**

```bash
python scripts/fix_imports.py
```

Expected output: ~25-35 files updated. No errors.

**Step 3: Spot-check key files**

```bash
grep -n "^from\|^import" src/main.py
grep -n "^from\|^import" src/core/db.py
grep -n "^from\|^import" src/ui/main_window.py
grep -n "^from\|^import" src/ui/dialogs/add_item_dialog.py
```

Verify:
- `src/main.py` shows `from core.config`, `from core.db`, `from ui.theme_config`, `from ui.main_window`, etc.
- `src/core/db.py` shows `from core.models` (not `from models`)
- `src/ui/main_window.py` shows `from core.services`, `from ui.dialogs.`, `from ui.widgets.`, etc.

**Step 4: Commit**

```bash
git add -A
git commit -m "chore: update all imports for src/ restructure"
```

---

### Task 8: Fix runtime.py get_base_path()

`runtime.py` is now at `src/runtime.py`. In dev mode it must return the **project root** (not `src/`), so that `resource_path("alembic.ini")` and `resource_path("icon.ico")` still resolve correctly. The one path that changes is the `.ui` file.

**Step 1: Edit `src/runtime.py`**

Change `get_base_path()` from:
```python
return os.path.dirname(os.path.abspath(__file__))
```
to:
```python
# runtime.py is at src/runtime.py; project root is two levels up
return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
```

Full updated function:
```python
def get_base_path() -> str:
    """Get the base path for resource files.

    When running from a PyInstaller bundle, files are in sys._MEIPASS.
    When running from source, returns the project root directory.

    Returns:
        Base path string.
    """
    if getattr(sys, "frozen", False):
        return sys._MEIPASS
    # runtime.py lives at src/runtime.py; project root is two levels up
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
```

**Step 2: Update the `.ui` path in `src/ui/main_window.py`**

Find the `uic.loadUi` call (currently `resource_path("ui/MainWindow.ui")`) and change it to:
```python
uic.loadUi(resource_path("src/ui/forms/MainWindow.ui"), self)
```

**Step 3: Verify the resource_path logic mentally**

| Call | Dev result | Frozen result |
|------|------------|---------------|
| `resource_path("alembic.ini")` | `<root>/alembic.ini` ✓ | `_MEIPASS/alembic.ini` ✓ |
| `resource_path("icon.ico")` | `<root>/icon.ico` ✓ | `_MEIPASS/icon.ico` ✓ |
| `resource_path("src/ui/forms/MainWindow.ui")` | `<root>/src/ui/forms/MainWindow.ui` ✓ | `_MEIPASS/src/ui/forms/MainWindow.ui` ✓ |

**Step 4: Commit**

```bash
git add src/runtime.py src/ui/main_window.py
git commit -m "fix: update runtime.py base path and ui file path for src/ layout"
```

---

### Task 9: Update AuditMagic.spec

**File:** `AuditMagic.spec`

**Step 1: Update entry point and data paths**

Change line `['main.py']` → `['src/main.py']`

Change the `.ui` file data entry:
```python
# Before
('ui/MainWindow.ui', 'ui'),
# After
('src/ui/forms/MainWindow.ui', 'src/ui/forms'),
```

The `alembic.ini`, `alembic`, and icon entries are unchanged (they stay at root).

Full updated `datas` section:
```python
datas=[
    ('src/ui/forms/MainWindow.ui', 'src/ui/forms'),
    ('alembic.ini', '.'),
    ('alembic', 'alembic'),
    (qt_material_path, 'qt_material'),
    (openpyxl_path, 'openpyxl'),
    *_extra_datas,
],
```

**Step 2: Commit**

```bash
git add AuditMagic.spec
git commit -m "fix: update AuditMagic.spec for src/ layout"
```

---

### Task 10: Update alembic/env.py

The import fix script already updated the `from db import` and `from models import` lines. But the `sys.path.insert` line also needs updating to point to `src/` instead of the project root.

**File:** `alembic/env.py`

**Step 1: Check current sys.path line**

```bash
grep -n "sys.path" alembic/env.py
```

**Step 2: Update the sys.path line**

Change:
```python
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
```
to:
```python
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "src"))
```

**Step 3: Verify imports now say `core.`**

```bash
grep -n "^from\|^import" alembic/env.py
```

Expected: `from core.db import DATABASE_URL` and `from core.models import Base`.

**Step 4: Commit**

```bash
git add alembic/env.py
git commit -m "fix: update alembic/env.py sys.path and imports for src/ layout"
```

---

### Task 11: Update mypy.ini and Create conftest.py

**Step 1: Add `mypy_path` to `mypy.ini`**

Open `mypy.ini` and add this line under `[mypy]`:
```ini
mypy_path = src
```

**Step 2: Create `tests/conftest.py`**

```python
import sys
import os

# Allow test files to import from src/ without installing the package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
```

**Step 3: Move `test_serialized_feature.py` from root to `tests/`**

```bash
git mv test_serialized_feature.py tests/test_serialized_feature.py
```

**Step 4: Commit**

```bash
git add mypy.ini tests/conftest.py tests/test_serialized_feature.py
git commit -m "chore: update mypy.ini, add conftest.py, move test to tests/"
```

---

### Task 12: Verify Tests Pass

**Step 1: Run the full test suite**

```bash
python -m pytest tests/ -v
```

Expected: all tests pass. If any fail with `ModuleNotFoundError`, the import replacement script missed something — fix the specific import manually and re-run.

**Step 2: Verify the app can at least import without crashing**

```bash
python -c "import sys; sys.path.insert(0, 'src'); import main"
```

Expected: no output (no errors on import).

**Step 3: Fix any remaining import errors**

If `pytest` or the import check reveals missed imports, fix them manually. Common pattern:
```bash
grep -rn "from ui_entities" src/ tests/   # should return nothing
grep -rn "^from models\b" src/ tests/     # should return nothing
grep -rn "^from services\b" src/ tests/   # should return nothing
```
All should return empty. If not, fix the remaining files.

**Step 4: Commit any fixes**

```bash
git add -A
git commit -m "fix: resolve remaining import errors after src/ restructure"
```

---

### Task 13: Update CLAUDE.md

**File:** `CLAUDE.md`

**Step 1: Update the Project Structure section**

Replace the old file listing under `## Project Structure` with the new layout. Key changes:
- `main.py` → `src/main.py`
- `models.py` → `src/core/models.py`
- `repositories.py` → `src/core/repositories.py`
- `services.py` → `src/core/services.py`
- `db.py` → `src/core/db.py`
- `config.py` → `src/core/config.py`
- `logger.py` → `src/core/logger.py`
- `styles.py` → `src/ui/styles.py`
- `theme_config.py` → `src/ui/theme_config.py`
- `theme_manager.py` → `src/ui/theme_manager.py`
- `validators.py` → `src/ui/validators.py`
- `ui_entities/` → replaced by `src/ui/` with subdirs `dialogs/`, `widgets/`, `models/`
- `ui/` → replaced by `src/ui/forms/`

Also update the **Running** section:
```bash
## Running
python src/main.py
```

And any import examples in the Architecture or Key Patterns sections.

**Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md for src/ restructure"
```

---

### Task 14: Final Smoke Test

**Step 1: Run tests one more time**

```bash
python -m pytest tests/ -v
```

Expected: all pass.

**Step 2: Verify no stale references to old paths**

```bash
grep -rn "ui_entities" src/ tests/ alembic/ --include="*.py"
grep -rn "from models import\|from services import\|from repositories import" src/ tests/ --include="*.py"
```

Both should return empty.

**Step 3: Check git log looks clean**

```bash
git log --oneline -15
```

Expected: a series of clean, descriptive commits for this restructure.
