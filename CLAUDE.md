# AuditMagic

PyQt6 desktop app for inventory. Have Material Design theme.

## Tech Stack
- Python 3.14+
- PyQt6 (GUI framework)
- SQLAlchemy + SQLite (database)
- Alembic (database migrations)
- qt-material (Material Design themes, light/dark mode)
- Black formatter
- IDE: PyCharm
- Virtual environment: `.venv`

## Project Structure
```
AuditMagic.spec      # PyInstaller build specification
alembic.ini          # Alembic configuration
mypy.ini             # MyPy configuration
requirements.txt     # Core dependencies
requirements-dev.txt # Dev dependencies (pytest, black, mypy, flake8, isort, pyinstaller)
.github/workflows/
  build.yml          # GitHub Actions: build & release on version tag push
  test.yml           # Runs pytest on every push/PR
  build-windows-hosted.yml  # [TEMP] manual workflow_dispatch build on GitHub-hosted runners
scripts/             # One-off helpers: generate_icons.py, extract_splash.py, fix_imports.py
alembic/             # Database migration scripts
  versions/          # Migration files
src/
  main.py            # Entry point with theme initialization and update checker
  version.py         # Single source of truth for app version (__version__)
  runtime.py         # PyInstaller resource path helpers (resource_path)
  update_checker.py  # GitHub release update checker (check_for_update, UpdateInfo)
  auto_updater.py    # Download worker + in-process exe swap (apply_update, cleanup_old_update)
  core/
    config.py        # Configuration management (JSON, dot-notation)
    logger.py        # Centralized logging system
    db.py            # Database init, session management, migrations
    models.py        # SQLAlchemy models (ItemType, Item, Transaction, Location, SearchHistory)
    repositories.py  # Data access layer (ItemTypeRepository, ItemRepository, TransactionRepository, LocationRepository, SearchHistoryRepository)
    services.py      # Business logic (InventoryService, SearchService, TransactionService)
    export_service.py # Excel export logic
  ui/
    main_window.py   # Main window controller with theme menu
    theme_config.py  # Theme configuration with enum-based parameters
    theme_manager.py # Theme management (light/dark modes)
    styles.py        # Centralized UI styles (complements qt-material)
    translations.py  # i18n (Ukrainian/English)
    validators.py    # QValidator subclasses and validation helpers
    forms/
      MainWindow.ui  # Qt Designer main window layout
    dialogs/
      add_item_chooser_dialog.py       # "With/Without Serial Number" chooser shown by "Add New Item"
      add_serialized_item_dialog.py    # Add serialized item form (type, subtype, serial number, notes, location)
      add_non_serialized_item_dialog.py # Add non-serialized item form (type, subtype, quantity, notes, location)
      wrapping_text_edit.py            # Shared WrappingTextEdit (word-wraps placeholder text); used by dialogs
      edit_item_dialog.py          # Edit item form; read-only serialized badge; conflict detection
      add_serial_number_dialog.py  # Add serial number to existing type
      remove_serial_number_dialog.py # Remove serial numbers from group
      item_details_dialog.py       # Item details view
      quantity_dialog.py           # Add/remove quantity dialog
      transactions_dialog.py       # Transaction history filtered by ItemType and date range
      all_transactions_dialog.py   # Cross-type transaction log with location filter and date range
      transfer_dialog.py           # Transfer items between locations (serialized + non-serialized)
      location_management_dialog.py # CRUD for locations (add/rename/delete)
      first_location_dialog.py     # First-launch wizard for creating the initial location
      export_options_dialog.py     # Export settings dialog
      update_dialog.py             # Update notification dialog (shown on startup if newer version)
    widgets/
      inventory_list_view.py # Custom QListView with context menu
      inventory_delegate.py  # Custom rendering with serialized/non-serialized pill badge
      location_selector.py   # LocationSelectorWidget — dropdown + "Manage" button above list
      search_widget.py       # Search with autocomplete and "Search all locations" checkbox
    models/
      inventory_item.py  # Item dataclasses (InventoryItem, GroupedInventoryItem DTOs)
      inventory_model.py # QAbstractListModel for items
tests/
  conftest.py                  # Adds src/ to sys.path for pytest
  test_serialized_feature.py   # Automated tests for is_serialized feature (34 checks)
  test_export_service.py
  test_export_transactions.py
```

## Setup
```bash
# Activate virtual environment
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt
```
Dev tools not on PATH — run venv-qualified (`.venv/bin/mypy`, `.venv/bin/black`, `.venv/bin/flake8`, `.venv/bin/pre-commit`). Only `pytest` work globally.

## Running
```bash
python src/main.py
```

## Code Intelligence (LSP)
Need `pyright-lsp` plugin installed and `pyright` on PATH.

- **LSP better than grep/Read for symbol hunt**: `goToDefinition`, `findReferences`, `workspaceSymbol`, `documentSymbol`, `hover`, `incomingCalls`/`outgoingCalls`.
- Before touch method signature or behavior (e.g. `add_quantity()`, `remove_quantity()`, `delete_by_serial_numbers()`, `_detach()`), use `findReferences` first, find every call site across `repositories.py`, `services.py`, `ui/`.
- Trust LSP result — no need re-open file with Read to double-check def or reference list already given.
- Use grep/ripgrep only for non-symbol text: strings in `translations.py`, comments, config values, TODOs, patterns spanning non-Python files (`.ui`, `.json`).
- After edit, check LSP diagnostics before move on; fix type error or missing import right away, don't wait for next `mypy` run.

## Code Conventions
- Type hints on all functions
- Docstrings for classes and public methods
- snake_case for functions/variables
- PascalCase for classes
- Private methods: `_method_name`
- Format with Black
- Line length 88; imports via `isort --profile black`
- flake8: hook's `--extend-ignore=E203` **override** `.flake8`, so bare `flake8` flag E203 on Black-formatted slices while hook pass fine. Match hook: `flake8 --extend-ignore=E203`. (`.flake8`'s W503/W504 already flake8 default — redundant.)
- Pre-commit hooks (`pre-commit install`): black, isort, flake8, trailing-whitespace, end-of-file-fixer, check-yaml, check-added-large-files, check-merge-conflict. **mypy not a hook.**
- Type check: `.venv/bin/mypy src` — clean right now. Config in `mypy.ini`; PyQt6/qt_material/alembic/openpyxl/requests/pyi_splash imports ignored
- `src/` got no `__init__.py`: it a path entry (conftest, PyInstaller `pathex`), not package. Add one and `mypy_path = src` map every file to two module names, mypy abort "Source file found twice" before check anything
- Models use SQLAlchemy 2.0 typed style (`Mapped[...]` + `mapped_column`). Tests build schema with `create_all` while users get theirs from Alembic, so two must agree — `tests/test_schema_parity.py` run every migration into temp DB, compare nullability, defaults, types, uniqueness against `create_all`. Fail on drift; don't weaken it to force model change pass

## Testing
```bash
QT_QPA_PLATFORM=offscreen pytest tests/ -v   # offscreen is REQUIRED — Qt aborts headless without it
```
- `tests/conftest.py` set `AUDITMAGIC_DB=:memory:` and autouse `fresh_db` fixture call `init_database(":memory:")` before every test — no DB setup needed in test body
- Test files: `test_repositories.py`, `test_services.py`, `test_dto_models.py`, `test_export_service.py`, `test_export_transactions.py`, `test_serialized_feature.py`, `test_auto_updater.py`, `test_translations.py`, `test_schema_parity.py`
- CI (`.github/workflows/test.yml`) run on every push/PR — Ubuntu, Python 3.14, same offscreen env
- Baseline: 170 test pass, `mypy src` clean

## Architecture
- MVC pattern with QAbstractListModel
- Repository → Service → UI layer stack
- Custom delegates for list item render
- Custom QListView (InventoryListView) with context menu, signal-based action
- pyqtSignal for component talk
- Python dataclasses for data model (InventoryItem, GroupedInventoryItem as DTO)
- SQLAlchemy ORM with detached object pattern (copy before return from session)
- Alembic migration with batch mode for SQLite compat
- uic.loadUi() for .ui file load
- QValidator subclass for real-time input filter
- **Theme System**: Enum-based config in theme_config.py with qt-material tie-in
- **Centralized Styling**: Helper function for consistent widget style with theme-aware color/dimension

## UI Components

### InventoryListView
Custom QListView widget give enhanced inventory list function:
- **Built-in context menu** with action: Edit, Details, Add/Remove Quantity, Transactions, Delete
- **Signal-based architecture** for loose couple with main window
- **Double-click support** for quick jump to item details
- **Custom delegate** (InventoryItemDelegate) for rich item render
- **Signals**: `edit_requested`, `details_requested`, `delete_requested`, `add_quantity_requested`, `remove_quantity_requested`, `transactions_requested`

### EditItemDialog
Enhanced edit dialog, serialized item support:
- **Serial number management**: List all serial number for serialized item, with delete
- **Type-aware UI**: Read-only quantity for serialized item, editable for non-serialized
- **Bulk serial deletion**: Track deleted serial number via `get_deleted_serial_numbers()`
- **Edit reason**: Required note field for audit trail
- **Serialized badge**: Read-only green/grey badge show type's serialization state
- **Conflict detection**: Rename to existing type with different `is_serialized` show red label, block save

### AddSerialNumberDialog
Streamlined dialog, add new serialized item to existing ItemType:
- **Serial number field**: Required, validate for uniqueness against existing serial
- **Notes field**: Optional; pass as transaction note for non-first item
- Caller (`main_window`) call `InventoryService.create_serialized_item` on accept

### RemoveSerialNumberDialog
Dialog for pick serial number to delete from grouped serialized item:
- **Scrollable checkbox list** of all serial number in group
- **Dynamic counter**: "Selected: X of Y" update as checkbox toggle
- **Required notes field** for audit trail
- **Validation**: At least one must pick; can't pick all (use "Delete" instead)
- Make REMOVE transaction record for each deleted serial

### GroupedInventoryItem
Aggregated DTO that group all item of same ItemType into single list row:
- Store `item_ids`, `serial_numbers`, `total_quantity`, `item_count`
- Legacy compat property (`id`, `quantity`, `serial_number`) for uniform handle with InventoryItem

### Usage Pattern
```python
# In MainWindow
self.inventory_list = InventoryListView()
self.inventory_list.edit_requested.connect(self._on_edit_item)
self.inventory_list.details_requested.connect(self._on_details_item)
# ... connect other signals
```

## Translations
- Primary: Ukrainian
- Fallback: English
- Keys defined in `src/ui/translations.py`
- Hierarchical naming: `app.title`, `button.add`, `field.type`

## Data Model (Hierarchical Structure)

> `alembic/env.py` read `DATABASE_URL` from `core.db` at import time, got **no override** — not `-x`, not env var. Every `alembic` command therefore hit real user DB (`~/.local/share/AuditMagic/inventory.db`). To migrate throwaway DB, patch `core.db.DATABASE_URL` before call `command.upgrade`, like `tests/test_schema_parity.py` do.

### ItemType (Type Definitions)
- **ItemType**: `name`, `sub_type`, `is_serialized`, `details`
- Represent category/template for item (e.g., "Laptop - ThinkPad X1")
- One ItemType can have many Item
- `is_serialized`: **immutable** once type has any item — enforced in `get_or_create` (conflict guard), `update` (item-count guard)

### Location
- **Location**: `id`, `name` (unique, max 100 chars)
- Required: at least one location must exist always (enforced by first-launch wizard)
- Item FK to `location_id` (nullable for legacy data; auto-assign wizard on startup handle NULL row)
- `LocationRepository.get_count()`, `get_all()`, `get_by_id()`, `get_unassigned_item_count()`, `assign_all_unassigned()`

### Item (Inventory Instances)
- **Item**: `item_type_id` (FK), `quantity`, `serial_number`, `location_id` (FK to Location), `condition`
- Represent actual inventory unit
- If serialized: quantity=1, serial_number required and unique
- If not serialized: quantity>0, no serial_number allowed
- Database constraint enforce: `(serial_number IS NULL AND quantity > 0) OR (serial_number IS NOT NULL AND quantity = 1)`

### Transaction
- **Transaction**: `item_type_id` (FK, NOT NULL), `transaction_type` (ADD/REMOVE/EDIT/TRANSFER), `quantity_change`, `quantity_before`, `quantity_after`, `notes`, `serial_number`, `from_location_id` (FK, nullable), `to_location_id` (FK, nullable)
- Belong to **ItemType**, not Item — audit trail keep even when item deleted
- `serial_number` on transaction mark which serialized unit involved
- For **serialized item**: `quantity_before/after` reflect total group count (how many item of that type exist), not single item quantity (always 1)
- For **non-serialized item**: `quantity_before/after` reflect single Item row's quantity
- For **TRANSFER** transaction: `from_location_id`, `to_location_id` set; quantity_change = qty moved
- ItemType `details` = type description; Transaction `notes` = reason for change (required for EDIT, optional for ADD/REMOVE/TRANSFER)

## Theme System 🎨

### Overview
AuditMagic use **qt-material** for Material Design theme with **enum-based config system** for centralized theme manage.

### Available Themes
- **Light** (Blue) - `light_blue.xml`
- **Dark** (Blue) - `dark_blue.xml`

All theme param (color, dimension, qt-material theme file) stored in `Theme` enum value in `theme_config.py`.

### Theme Architecture
- **theme_config.py**: Enum-based theme config with ThemeParameters dataclass
  - `ThemeColors`: Color palette (main, secondary, borders, backgrounds, text)
  - `ThemeDimensions`: UI dimension (input height, button height, padding, font size)
  - `Theme` enum: Light and Dark theme definition
- **theme_manager.py**: Theme apply logic with qt-material tie-in
- **styles.py**: Theme-aware style helper that fetch color/dimension from current theme
- Theme saved to user config, persist between session
- Access via **🎨 Theme** menu in main window

### Theme Configuration Structure
```python
# In theme_config.py
LIGHT = ThemeParameters(
    name="Light",
    mode="light",
    qt_material_theme="light_blue.xml",
    colors=ThemeColors(
        main="#282828",           # Main text
        secondary="#BBC8C3",      # Secondary
        border_default="#ccc",
        bg_default="#ffffff",
        bg_hover="#f0f0f0",
        bg_disabled="#e0e0e0",
        text_secondary="#666666",
        text_disabled="#999999"
    ),
    dimensions=ThemeDimensions(
        input_height=28,
        button_height=25,
        button_min_width=100,
        button_padding=10,
        border_radius=4,
        font_size=13,
        font_size_large=14
    )
)
```

### Applying Themes Programmatically
```python
from theme_manager import get_theme_manager
from theme_config import Theme

tm = get_theme_manager()
tm.apply_theme(Theme.DARK)      # Apply dark theme
tm.apply_theme(Theme.LIGHT)     # Apply light theme
tm.toggle_theme()               # Switch between light/dark
```

### Styling System
- **qt-material**: Give base Material Design theme
- **theme_config.py**: Centralized theme param in enum value
- **styles.py**: Theme-aware helper fetch from current theme
- **Helper functions**: `apply_input_style()`, `apply_button_style()`, `apply_text_edit_style()`, `apply_combo_box_style()`
- **Utility classes**: `Colors` (theme-aware color access), `Dimensions` (theme-aware dimension access), `Styles` (stylesheet generator)
- **Dynamic dimensions**: All widget get size from `get_theme_dimensions()`
- **Dynamic colors**: All widget get color from `get_theme_colors()`
- **Action button colors**: Constant (green, red, blue) with theme-aware disabled state

### Theme-Aware Color and Dimension Access
```python
from theme_config import get_theme_colors, get_theme_dimensions

# Access current theme colors
colors = get_theme_colors()
main_color = colors.main
border_color = colors.border_default

# Access current theme dimensions
dims = get_theme_dimensions()
input_height = dims.input_height
button_height = dims.button_height
```

### Style Application Example
```python
from styles import apply_input_style, apply_button_style

# Apply to input field (automatically uses theme dimensions/colors)
apply_input_style(line_edit, large=True)

# Apply to buttons with different variants
apply_button_style(save_button, "primary")    # Green
apply_button_style(cancel_button, "danger")   # Red
apply_button_style(info_button, "info")       # Blue
apply_button_style(other_button, "secondary") # Outline
```

## Configuration
User prefs stored in `~/.local/share/AuditMagic/config.json` (Linux) or `%LOCALAPPDATA%\AuditMagic\config.json` (Windows):

```json
{
  "language": "uk",
  "theme": "Light",
  "window": {
    "geometry": "...",
    "maximized": false
  },
  "ui": {
    "show_tooltips": true,
    "confirm_delete": true,
    "date_format": "dd.MM.yyyy"
  }
}
```

**Note**: Theme now stored as simple string name (e.g., "Light", "Dark") matching `Theme` enum value.

## Logging
- Centralized logging via `logger.py`
- Logs stored in `~/.local/share/AuditMagic/logs/` (Linux) or `%LOCALAPPDATA%\AuditMagic\logs\` (Windows)
- File: `audit_magic_YYYYMMDD.log`
- Levels: DEBUG (file), WARNING+ (console)

## Key Patterns
- Form validation with QMessageBox feedback, QValidator subclass
- Custom InventoryListView widget with built-in context menu, signal
- Context menu action: Edit, Details, Add/Remove Quantity, Transactions, Transfer, Delete
- Double-click open details dialog
- Modal dialog for all CRUD op
- **Location system**: Item belong to a `Location` (FK). `LocationSelectorWidget` above list filter view. "All Locations" (None) show everything. Config key `ui.last_location_id` persist selection (sentinel pattern: missing key → first location, null → All Locations, int → validate + fallback).
- **First-launch wizard**: `FirstLocationDialog` loop until at least one location exist. `_ensure_location_exists()` call before any list load.
- **Transfer**: `InventoryService.transfer_item(item_id, qty, to_location_id, notes)` / `transfer_serialized_items(item_ids, to_location_id, notes)`. Make TRANSFER transaction with `from_location_id`, `to_location_id`.
- **All Transactions view**: `AllTransactionsDialog` show cross-type log, filter by location + date range. 10 column including From/To Location.
- **`InventoryItem.location_id / location_name`**: replace old `location: str` field. Backward-compat `.location` property return `location_name`.
- **Type-centric transactions**: Transaction.item_type_id (NOT NULL) is sole FK — no item_id. Audit trail survive item deletion. `serial_number` on transaction record mark specific unit.
- **Serialized item creation**: use `ItemRepository.create_serialized` / `InventoryService.create_serialized_item` (not generic `create`). These count existing item of type first, set `quantity_before/after` right for grouped view. Notes policy: first item get `tr("transaction.notes.initial")` no matter caller input; later items use caller-given note or `""`.
- **ItemType deletion**: `InventoryService.delete_item_type` → `ItemTypeRepository.delete`. Deletion order: (1) Transaction row via `sql_delete` (FK NOT NULL, no ORM cascade), (2) Item row via ORM cascade from ItemType, (3) ItemType itself.
- `delete_by_serial_numbers`: flush REMOVE transaction first, then delete item via direct SQL (`sql_delete`) to skip ORM cascade, keep audit record
- GroupedInventoryItem aggregation: item grouped by ItemType in list view; both `InventoryItem`, `GroupedInventoryItem` expose `item_type_id`
- Shared private helper in repository to avoid query duplicate (e.g., `_get_types_with_items`)
- **`is_serialized` immutability**: `ItemTypeRepository.get_or_create` raise `ValueError` on conflict; `update` raise if item exist. UI pre-fill, lock checkbox when user type existing type name in AddItemDialog.
- `ItemTypeRepository.get_by_name_and_subtype` / `InventoryService.get_item_type_by_name_subtype`: live lookup used by dialog to spot existing type while user type
- Serialized badge colors: green `#2e7d32` (serialized) / grey `#757575` (non-serialized) — fixed for accessibility, not theme-dependent
- Serialized item management: serial number list, delete in edit dialog
- Centralized style with helper function
- Theme switch with instant preview
- Config persist with dot-notation access
- Enum-based theme config for maintainability

## Auto-Update System

### Version Management
- Version defined in `version.py` (`__version__`)
- Show in main window title bar as `"<title> v<version>"`
- Compared against GitHub Releases API every startup

### Packaging (PyInstaller)
- Spec file: `AuditMagic.spec`
- Bundled data: `ui/MainWindow.ui`, `alembic/`, `alembic.ini`, `qt_material`
- Resource path resolved via `runtime.resource_path()` (handle both dev, bundled mode)
- Build: `pyinstaller AuditMagic.spec`
- Output: `dist/AuditMagic.exe`

### Update Checker
- Check `https://api.github.com/repos/Chevit/AuditMagic/releases/latest`
- Run in `UpdateCheckWorker(QThread)` on startup — non-blocking
- Show `UpdateDialog` with download/skip button if newer version found
- Use `urllib` (stdlib only — no extra dependency)

### Release Process
1. Tag: `git tag vX.Y.Z`
2. Push: `git push && git push --tags`
3. GitHub Actions inject version from tag, build `.exe`, make release auto

> `build.yml`'s Windows job run on a **`self-hosted`** runner (macOS/Linux job commented out). If stall, runner offline — use `build-windows-hosted.yml` via workflow_dispatch (GitHub-hosted, Python 3.13 for Windows, take optional version input).

> Note: `version.py` hold `0.0.0-dev` placeholder in source. Real version inject by CI at build time — don't hand-edit `__version__` before tag.

## Documentation
- **CLAUDE.md**: This file - project overview, convention
- **README.md**: Project readme
- **Instructions/**: Historical implementation guide (incl. `IMPROVEMENTS.md`) — legacy `ui_entities/` path, don't follow word-for-word
- **docs/HOW-TO.md**: Ukrainian end-user manual (linked from README)
- **docs/superpowers/specs/** + **plans/**: Design spec, plan, dated `YYYY-MM-DD-<feature>-design.md`; convention is `docs: add <x> design spec` committed before the `fix:`/`feat:` that build it