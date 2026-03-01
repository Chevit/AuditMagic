# AuditMagic

PyQt6 desktop inventory management application with Material Design theming.

## Tech Stack
- Python 3.11+
- PyQt6 (GUI framework)
- SQLAlchemy + SQLite (database)
- Alembic (database migrations)
- qt-material (Material Design themes with light/dark mode)
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
alembic/             # Database migration scripts
  versions/          # Migration files
src/
  main.py            # Entry point with theme initialization and update checker
  version.py         # Single source of truth for app version (__version__)
  runtime.py         # PyInstaller resource path helpers (resource_path)
  update_checker.py  # GitHub release update checker (check_for_update, UpdateInfo)
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
      add_item_dialog.py           # Add item form with optional "Initial Notes" field
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

## Running
```bash
python src/main.py
```

## Code Conventions
- Type hints on all functions
- Docstrings for classes and public methods
- snake_case for functions/variables
- PascalCase for classes
- Private methods: `_method_name`
- Format with Black

## Architecture
- MVC pattern with QAbstractListModel
- Repository → Service → UI layered architecture
- Custom delegates for list item rendering
- Custom QListView (InventoryListView) with context menu and signal-based actions
- pyqtSignal for component communication
- Python dataclasses for data models (InventoryItem and GroupedInventoryItem as DTOs)
- SQLAlchemy ORM with detached object pattern (copy before returning from session)
- Alembic migrations with batch mode for SQLite compatibility
- uic.loadUi() for .ui file loading
- QValidator subclasses for real-time input filtering
- **Theme System**: Enum-based configuration in theme_config.py with qt-material integration
- **Centralized Styling**: Helper functions for consistent widget styling with theme-aware colors/dimensions

## UI Components

### InventoryListView
Custom QListView widget providing enhanced inventory list functionality:
- **Built-in context menu** with actions: Edit, Details, Add/Remove Quantity, Transactions, Delete
- **Signal-based architecture** for loose coupling with main window
- **Double-click support** for quick access to item details
- **Custom delegate** (InventoryItemDelegate) for rich item rendering
- **Signals**: `edit_requested`, `details_requested`, `delete_requested`, `add_quantity_requested`, `remove_quantity_requested`, `transactions_requested`

### EditItemDialog
Enhanced edit dialog with serialized item support:
- **Serial number management**: Lists all serial numbers for serialized items with delete capability
- **Type-aware UI**: Read-only quantity for serialized items, editable for non-serialized
- **Bulk serial deletion**: Track deleted serial numbers via `get_deleted_serial_numbers()`
- **Edit reason**: Required notes field for audit trail
- **Serialized badge**: Read-only green/grey badge shows the type's serialization state
- **Conflict detection**: Renaming to an existing type with different `is_serialized` shows a red label and blocks save

### AddSerialNumberDialog
Streamlined dialog for adding a new serialized item to an existing ItemType:
- **Serial number field**: Required, validated for uniqueness against existing serials
- **Notes field**: Optional; passed as transaction notes for non-first items
- Caller (`main_window`) invokes `InventoryService.create_serialized_item` on accept

### RemoveSerialNumberDialog
Dialog for selecting serial numbers to delete from a grouped serialized item:
- **Scrollable checkbox list** of all serial numbers in the group
- **Dynamic counter**: "Selected: X of Y" updates as checkboxes are toggled
- **Required notes field** for audit trail
- **Validation**: At least one must be selected; cannot select all (use "Delete" instead)
- Creates REMOVE transaction records for each deleted serial

### GroupedInventoryItem
Aggregated DTO that groups all items of the same ItemType into a single list row:
- Stores `item_ids`, `serial_numbers`, `total_quantity`, `item_count`
- Legacy compatibility properties (`id`, `quantity`, `serial_number`) for uniform handling with InventoryItem

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
- Keys defined in `ui_entities/translations.py`
- Hierarchical naming: `app.title`, `button.add`, `field.type`

## Data Model (Hierarchical Structure)

### ItemType (Type Definitions)
- **ItemType**: `name`, `sub_type`, `is_serialized`, `details`
- Represents a category/template for items (e.g., "Laptop - ThinkPad X1")
- One ItemType can have many Items
- `is_serialized`: **immutable** once the type has any items — enforced in `get_or_create` (conflict guard) and `update` (item-count guard)

### Location
- **Location**: `id`, `name` (unique, max 100 chars)
- Required: at least one location must exist at all times (enforced by first-launch wizard)
- Items FK to `location_id` (nullable for legacy data; auto-assign wizard on startup handles NULL rows)
- `LocationRepository.get_count()`, `get_all()`, `get_by_id()`, `get_unassigned_item_count()`, `assign_all_unassigned()`

### Item (Inventory Instances)
- **Item**: `item_type_id` (FK), `quantity`, `serial_number`, `location_id` (FK to Location), `condition`
- Represents actual inventory units
- If serialized: quantity=1, serial_number required and unique
- If not serialized: quantity>0, no serial_number allowed
- Database constraint enforces: `(serial_number IS NULL AND quantity > 0) OR (serial_number IS NOT NULL AND quantity = 1)`

### Transaction
- **Transaction**: `item_type_id` (FK, NOT NULL), `transaction_type` (ADD/REMOVE/EDIT/TRANSFER), `quantity_change`, `quantity_before`, `quantity_after`, `notes`, `serial_number`, `from_location_id` (FK, nullable), `to_location_id` (FK, nullable)
- Belongs to **ItemType**, not Item — audit trail is preserved even when items are deleted
- `serial_number` on the transaction identifies the specific serialized unit involved
- For **serialized items**: `quantity_before/after` reflect the total group count (how many items of that type exist), not the individual item quantity (which is always 1)
- For **non-serialized items**: `quantity_before/after` reflect the single Item row's quantity
- For **TRANSFER** transactions: `from_location_id` and `to_location_id` are set; quantity_change = qty moved
- ItemType `details` = type description; Transaction `notes` = reason for change (required for EDIT, optional for ADD/REMOVE/TRANSFER)

## Theme System 🎨

### Overview
AuditMagic uses **qt-material** for Material Design theming with an **enum-based configuration system** for centralized theme management.

### Available Themes
- **Light** (Blue) - `light_blue.xml`
- **Dark** (Blue) - `dark_blue.xml`

All theme parameters (colors, dimensions, qt-material theme file) are stored in `Theme` enum values in `theme_config.py`.

### Theme Architecture
- **theme_config.py**: Enum-based theme configuration with ThemeParameters dataclass
  - `ThemeColors`: Color palette (main, secondary, borders, backgrounds, text)
  - `ThemeDimensions`: UI dimensions (input height, button height, padding, font sizes)
  - `Theme` enum: Light and Dark theme definitions
- **theme_manager.py**: Theme application logic with qt-material integration
- **styles.py**: Theme-aware styling helpers that fetch colors/dimensions from current theme
- Themes saved to user config and persist between sessions
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
- **qt-material**: Provides base Material Design theme
- **theme_config.py**: Centralized theme parameters in enum values
- **styles.py**: Theme-aware helpers that fetch from current theme
- **Helper functions**: `apply_input_style()`, `apply_button_style()`, `apply_text_edit_style()`, `apply_combo_box_style()`
- **Utility classes**: `Colors` (theme-aware color access), `Dimensions` (theme-aware dimension access), `Styles` (stylesheet generators)
- **Dynamic dimensions**: All widgets retrieve sizes from `get_theme_dimensions()`
- **Dynamic colors**: All widgets retrieve colors from `get_theme_colors()`
- **Action button colors**: Constant (green, red, blue) with theme-aware disabled states

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
User preferences stored in `~/.local/share/AuditMagic/config.json` (Linux) or `%LOCALAPPDATA%\AuditMagic\config.json` (Windows):

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

**Note**: Theme is now stored as a simple string name (e.g., "Light", "Dark") matching the `Theme` enum values.

## Logging
- Centralized logging via `logger.py`
- Logs stored in `~/.local/share/AuditMagic/logs/` (Linux) or `%LOCALAPPDATA%\AuditMagic\logs\` (Windows)
- File: `audit_magic_YYYYMMDD.log`
- Levels: DEBUG (file), WARNING+ (console)

## Key Patterns
- Form validation with QMessageBox feedback and QValidator subclasses
- Custom InventoryListView widget with built-in context menus and signals
- Context menu actions: Edit, Details, Add/Remove Quantity, Transactions, Transfer, Delete
- Double-click opens details dialog
- Modal dialogs for all CRUD operations
- **Location system**: Items belong to a `Location` (FK). `LocationSelectorWidget` above list filters view. "All Locations" (None) shows everything. Config key `ui.last_location_id` persists selection (sentinel pattern: missing key → first location, null → All Locations, int → validate + fallback).
- **First-launch wizard**: `FirstLocationDialog` loops until at least one location exists. `_ensure_location_exists()` called before any list load.
- **Transfer**: `InventoryService.transfer_item(item_id, qty, to_location_id, notes)` / `transfer_serialized_items(item_ids, to_location_id, notes)`. Creates TRANSFER transaction with `from_location_id` and `to_location_id`.
- **All Transactions view**: `AllTransactionsDialog` shows cross-type log filterable by location + date range. 10 columns including From/To Location.
- **`InventoryItem.location_id / location_name`**: replaces old `location: str` field. Backward-compat `.location` property returns `location_name`.
- **Type-centric transactions**: Transaction.item_type_id (NOT NULL) is the sole FK — no item_id. Audit trail survives item deletion. `serial_number` on the transaction record identifies the specific unit.
- **Serialized item creation**: use `ItemRepository.create_serialized` / `InventoryService.create_serialized_item` (not the generic `create`). These count existing items of the type first to set `quantity_before/after` correctly for the grouped view. Notes policy: first item gets `tr("transaction.notes.initial")` regardless of caller input; subsequent items use caller-supplied notes or `""`.
- **ItemType deletion**: `InventoryService.delete_item_type` → `ItemTypeRepository.delete`. Deletion order: (1) Transaction rows via `sql_delete` (FK NOT NULL, no ORM cascade), (2) Item rows via ORM cascade from ItemType, (3) ItemType itself.
- `delete_by_serial_numbers`: flushes REMOVE transactions first, then deletes items via direct SQL (`sql_delete`) to bypass ORM cascade, preserving audit records
- GroupedInventoryItem aggregation: items grouped by ItemType in list view; both `InventoryItem` and `GroupedInventoryItem` expose `item_type_id`
- Shared private helpers in repositories to avoid query duplication (e.g., `_get_types_with_items`)
- **`is_serialized` immutability**: `ItemTypeRepository.get_or_create` raises `ValueError` on conflict; `update` raises if items exist. UI pre-fills and locks the checkbox when the user types an existing type name in AddItemDialog.
- `ItemTypeRepository.get_by_name_and_subtype` / `InventoryService.get_item_type_by_name_subtype`: live lookup used by dialogs to detect existing types while user types
- Serialized badge colors: green `#2e7d32` (serialized) / grey `#757575` (non-serialized) — fixed for accessibility, not theme-dependent
- Serialized item management: serial number listing, deletion in edit dialog
- Centralized styling with helper functions
- Theme switching with instant preview
- Configuration persistence with dot-notation access
- Enum-based theme configuration for maintainability

## Auto-Update System

### Version Management
- Version defined in `version.py` (`__version__`)
- Displayed in main window title bar as `"<title> v<version>"`
- Compared against GitHub Releases API on every startup

### Packaging (PyInstaller)
- Spec file: `AuditMagic.spec`
- Bundled data: `ui/MainWindow.ui`, `alembic/`, `alembic.ini`, `qt_material`
- Resource paths resolved via `runtime.resource_path()` (handles both dev and bundled modes)
- Build: `pyinstaller AuditMagic.spec`
- Output: `dist/AuditMagic.exe`

### Update Checker
- Checks `https://api.github.com/repos/Chevit/AuditMagic/releases/latest`
- Runs in `UpdateCheckWorker(QThread)` on startup — non-blocking
- Shows `UpdateDialog` with download/skip buttons if newer version found
- Uses `urllib` (stdlib only — no extra dependencies)

### Release Process
1. Update `__version__` in `version.py`
2. Commit: `git commit -am "Bump version to X.Y.Z"`
3. Tag: `git tag vX.Y.Z`
4. Push: `git push && git push --tags`
5. GitHub Actions builds `.exe` and creates a release automatically

## Documentation
- **CLAUDE.md**: This file - project overview and conventions
- **README.md**: Project readme
- **IMPROVEMENTS.md**: Improvement guide with step-by-step instructions
