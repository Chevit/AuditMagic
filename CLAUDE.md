# AuditMagic

PyQt6 desktop inventory management application.

## Tech Stack
- Python 3.11+
- PyQt6
- SQLAlchemy + SQLite
- Alembic (database migrations)
- Black formatter
- IDE: PyCharm
- Virtual environment: `.venv`

## Project Structure
```
main.py              # Entry point
config.py            # Configuration management (JSON, dot-notation)
db.py                # Database init, session management, migrations
models.py            # SQLAlchemy models (Item, Transaction, SearchHistory)
repositories.py      # Data access layer (ItemRepository, TransactionRepository)
services.py          # Business logic (InventoryService, SearchService)
validators.py        # QValidator subclasses and validation helpers
alembic/             # Database migration scripts
  versions/          # Migration files
ui/                  # Qt Designer .ui files
ui_entities/         # UI components and models
  main_window.py     # Main window controller
  inventory_model.py # QAbstractListModel for items
  inventory_item.py  # Item dataclass (DTO)
  inventory_delegate.py # Custom rendering
  translations.py    # i18n (Ukrainian/English)
  add_item_dialog.py # Add item form
  edit_item_dialog.py # Edit item form with reason field
  item_details_dialog.py # Item details view
  quantity_dialog.py # Add/remove quantity dialog
  transactions_dialog.py # Transaction history view
  search_widget.py   # Search with autocomplete
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

## Key Patterns
- Form validation with QMessageBox feedback and QValidator subclasses
- Context menus on list items (Edit, Details, Delete)
- Double-click opens details dialog
- Modal dialogs for all CRUD operations
- Transaction audit trail for all inventory changes
