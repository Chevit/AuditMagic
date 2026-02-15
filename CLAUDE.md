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
main.py              # Entry point with theme initialization
config.py            # Configuration management (JSON, dot-notation)
logger.py            # Centralized logging system
theme_config.py      # Theme configuration with enum-based parameters
theme_manager.py     # Theme management (light/dark modes)
styles.py            # Centralized UI styles (complements qt-material)
db.py                # Database init, session management, migrations
models.py            # SQLAlchemy models (Item, Transaction, SearchHistory)
repositories.py      # Data access layer (ItemRepository, TransactionRepository)
services.py          # Business logic (InventoryService, SearchService)
validators.py        # QValidator subclasses and validation helpers
alembic/             # Database migration scripts
  versions/          # Migration files
ui/                  # Qt Designer .ui files
ui_entities/         # UI components and models
  main_window.py     # Main window controller with theme menu
  inventory_list_view.py # Custom QListView with context menu
  inventory_model.py # QAbstractListModel for items
  inventory_item.py  # Item dataclass (DTO)
  inventory_delegate.py # Custom rendering
  translations.py    # i18n (Ukrainian/English)
  add_item_dialog.py # Add item form with custom styling
  edit_item_dialog.py # Edit item form with reason field
  item_details_dialog.py # Item details view
  quantity_dialog.py # Add/remove quantity dialog
  transactions_dialog.py # Transaction history view with filters
  search_widget.py   # Search with autocomplete and styled inputs
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
python main.py
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
- Python dataclasses for data models (InventoryItem as DTO)
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

## Data Model
- **Item**: `item_type`, `sub_type`, `quantity`, `serial_number`, `details` (item description)
- **Transaction**: `item_id`, `transaction_type` (ADD/REMOVE/EDIT), `quantity_change`, `quantity_before`, `quantity_after`, `notes` (reason)
- Item `details` = item description; Transaction `notes` = reason for change (separate concepts)
- Edit action creates a single EDIT transaction (not separate ADD/REMOVE + EDIT)

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
- **Helper functions**: `apply_input_style()`, `apply_button_style()`, `apply_text_edit_style()`
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
- Context menu actions: Edit, Details, Add/Remove Quantity, Transactions, Delete
- Double-click opens details dialog
- Modal dialogs for all CRUD operations
- Transaction audit trail for all inventory changes
- Centralized styling with helper functions
- Theme switching with instant preview
- Configuration persistence with dot-notation access
- Enum-based theme configuration for maintainability

## Documentation
- **CLAUDE.md**: This file - project overview and conventions
- **DIMENSION_GUIDE.md**: Complete guide to theme dimensions (heights, widths, padding, fonts)
- **THEME_SYSTEM_REFACTOR.md**: Documentation of theme system refactor
- **THEME_FIXES.md**: Theme-related fixes and improvements
- **IMPLEMENTATION_GUIDE.md**: Detailed implementation guide (if applicable)
