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
theme_manager.py     # Theme management (light/dark + color variants)
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
- pyqtSignal for component communication
- Python dataclasses for data models (InventoryItem as DTO)
- SQLAlchemy ORM with detached object pattern (copy before returning from session)
- Alembic migrations with batch mode for SQLite compatibility
- uic.loadUi() for .ui file loading
- QValidator subclasses for real-time input filtering
- **Theme System**: qt-material for base theming + styles.py for customizations
- **Centralized Styling**: Helper functions for consistent widget styling

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
AuditMagic uses **qt-material** for Material Design theming with full light/dark mode support.

### Available Themes
- **2 Modes**: Light and Dark
- **6 Color Variants**: Default (Blue), Teal, Cyan, Purple, Pink, Amber
- **Total**: 12 unique theme combinations

### Theme Management
- `theme_manager.py` - Theme switching logic
- `styles.py` - Additional custom styles that complement qt-material
- Themes saved to user config and persist between sessions
- Access via **🎨 Theme** menu in main window

### Applying Themes Programmatically
```python
from theme_manager import get_theme_manager

tm = get_theme_manager()
tm.apply_theme("dark", "teal")  # Dark mode with teal accent
tm.toggle_theme()               # Switch between light/dark
tm.set_variant("purple")        # Change color variant
```

### Styling System
- **qt-material**: Provides base Material Design theme
- **styles.py**: Adds custom refinements with theme-aware colors
- **Helper functions**: `apply_input_style()`, `apply_button_style()`, `apply_text_edit_style()`
- **Consistent dimensions**: All widgets use standardized sizes from `Dimensions` class
- **Color palette**: Defined in `Colors` class with custom colors:
  - **Dark mode**: Main text #d3d3d3, Secondary #130512
  - **Light mode**: Main text #282828, Secondary #BBC8C3
  - **Action buttons**: Constant colors (green, red, blue) with theme-aware disabled states

### Style Application Example
```python
from styles import apply_input_style, apply_button_style

# Apply to input field
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
  "theme": {
    "mode": "light",
    "variant": "default"
  },
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

## Logging
- Centralized logging via `logger.py`
- Logs stored in `~/.local/share/AuditMagic/logs/` (Linux) or `%LOCALAPPDATA%\AuditMagic\logs\` (Windows)
- File: `audit_magic_YYYYMMDD.log`
- Levels: DEBUG (file), WARNING+ (console)

## Key Patterns
- Form validation with QMessageBox feedback and QValidator subclasses
- Context menus on list items (Edit, Details, Delete)
- Double-click opens details dialog
- Modal dialogs for all CRUD operations
- Transaction audit trail for all inventory changes
- Centralized styling with helper functions
- Theme switching with instant preview
- Configuration persistence with dot-notation access
