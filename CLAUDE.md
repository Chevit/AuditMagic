# AuditMagic

PyQt6 desktop inventory management application.

## Tech Stack
- Python 3.11+
- PyQt6
- Black formatter
- IDE: PyCharm
- Virtual environment: `.venv`

## Project Structure
```
main.py              # Entry point
ui/                  # Qt Designer .ui files
ui_entities/         # UI components and models
  main_window.py     # Main window controller
  inventory_model.py # QAbstractListModel for items
  inventory_item.py  # Item dataclass
  inventory_delegate.py # Custom rendering
  translations.py    # i18n (Ukrainian/English)
  add_item_dialog.py # Add item form
  item_details_dialog.py # Item details view
```

## Setup
```bash
# Activate virtual environment
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # macOS/Linux

# Install dependencies
pip install PyQt6
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
- Custom delegates for list item rendering
- pyqtSignal for component communication
- Python dataclasses for data models
- uic.loadUi() for .ui file loading

## Translations
- Primary: Ukrainian
- Fallback: English
- Keys defined in `ui_entities/translations.py`
- Hierarchical naming: `app.title`, `button.add`, `field.type`

## Key Patterns
- Form validation with QMessageBox feedback
- Context menus on list items (Edit, Details, Delete)
- Double-click opens details dialog
- Modal dialogs for all CRUD operations
