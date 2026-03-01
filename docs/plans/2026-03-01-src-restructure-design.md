# Design: src/ Project Restructure

**Date:** 2026-03-01
**Status:** Approved

## Goal

Reorganize the AuditMagic codebase from a flat root layout into a structured `src/` layout with `core/` and `ui/` subdirectories. Pure folder reorganization — no Python packaging (no installable package).

## Target Directory Structure

```
AuditMagic/
├── src/
│   ├── main.py
│   ├── version.py
│   ├── runtime.py
│   ├── update_checker.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── db.py
│   │   ├── export_service.py
│   │   ├── logger.py
│   │   ├── models.py
│   │   ├── repositories.py
│   │   └── services.py
│   └── ui/
│       ├── __init__.py
│       ├── main_window.py
│       ├── styles.py
│       ├── theme_config.py
│       ├── theme_manager.py
│       ├── translations.py
│       ├── validators.py
│       ├── forms/
│       │   └── MainWindow.ui
│       ├── dialogs/
│       │   ├── __init__.py
│       │   ├── add_item_dialog.py
│       │   ├── add_serial_number_dialog.py
│       │   ├── all_transactions_dialog.py
│       │   ├── edit_item_dialog.py
│       │   ├── export_options_dialog.py
│       │   ├── first_location_dialog.py
│       │   ├── item_details_dialog.py
│       │   ├── location_management_dialog.py
│       │   ├── quantity_dialog.py
│       │   ├── remove_serial_number_dialog.py
│       │   ├── transactions_dialog.py
│       │   ├── transfer_dialog.py
│       │   └── update_dialog.py
│       ├── widgets/
│       │   ├── __init__.py
│       │   ├── inventory_delegate.py
│       │   ├── inventory_list_view.py
│       │   ├── location_selector.py
│       │   └── search_widget.py
│       └── models/
│           ├── __init__.py
│           ├── inventory_item.py
│           └── inventory_model.py
├── tests/
│   ├── conftest.py             ← new: adds src/ to sys.path
│   ├── test_export_service.py
│   ├── test_export_transactions.py
│   └── test_serialized_feature.py  ← moved from root
├── alembic/
│   └── env.py                  ← updated sys.path + imports
├── docs/plans/
├── scripts/
├── Instructions/
├── .github/workflows/
├── alembic.ini                 ← unchanged
├── AuditMagic.spec             ← updated entry point + data paths
├── mypy.ini                    ← add mypy_path = src
├── requirements.txt
├── requirements-dev.txt
├── icon.ico / icon.icns / icon.png
├── CLAUDE.md
└── README.md
```

## Import Strategy

Running `python src/main.py` from project root causes Python to add `src/` to `sys.path`. All imports are absolute from `src/`:

```python
# Before                                    # After
from models import Item              →  from core.models import Item
from services import InventoryService →  from core.services import InventoryService
from ui_entities.main_window import  →  from ui.main_window import MainWindow
from ui_entities.add_item_dialog import → from ui.dialogs.add_item_dialog import ...
from styles import apply_button_style →  from ui.styles import apply_button_style
from theme_config import ...          →  from ui.theme_config import ...
```

Intra-package imports (e.g. a dialog importing from another dialog) are always absolute from `src/`.

## Tooling Changes

### AuditMagic.spec
- Entry point: `['main.py']` → `['src/main.py']`
- UI file data: `('ui/MainWindow.ui', 'ui')` → `('src/ui/forms/MainWindow.ui', 'ui/forms')`

### runtime.py
- File moves to `src/runtime.py` — `get_base_path()` in dev mode returns `<root>/src/` (correct; all assets are under `src/`)
- All callers update the path argument: `resource_path('ui/MainWindow.ui')` → `resource_path('ui/forms/MainWindow.ui')`

### alembic/env.py
```python
# sys.path line
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))
# imports
from core.db import DATABASE_URL
from core.models import Base
```

### tests/conftest.py (new file)
```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
```

### mypy.ini
Add `mypy_path = src` so mypy resolves `core.*` and `ui.*`.

### CI/CD (build.yml)
No changes — still runs `pyinstaller AuditMagic.spec` from root.

## File Classification

| File | New Location |
|------|-------------|
| main.py | src/main.py |
| version.py | src/version.py |
| runtime.py | src/runtime.py |
| update_checker.py | src/update_checker.py |
| config.py | src/core/config.py |
| db.py | src/core/db.py |
| export_service.py | src/core/export_service.py |
| logger.py | src/core/logger.py |
| models.py | src/core/models.py |
| repositories.py | src/core/repositories.py |
| services.py | src/core/services.py |
| styles.py | src/ui/styles.py |
| theme_config.py | src/ui/theme_config.py |
| theme_manager.py | src/ui/theme_manager.py |
| translations.py | src/ui/translations.py |
| validators.py | src/ui/validators.py |
| ui_entities/main_window.py | src/ui/main_window.py |
| ui_entities/*_dialog.py (13 files) | src/ui/dialogs/ |
| ui_entities/inventory_list_view.py | src/ui/widgets/ |
| ui_entities/inventory_delegate.py | src/ui/widgets/ |
| ui_entities/location_selector.py | src/ui/widgets/ |
| ui_entities/search_widget.py | src/ui/widgets/ |
| ui_entities/inventory_model.py | src/ui/models/ |
| ui_entities/inventory_item.py | src/ui/models/ |
| ui/MainWindow.ui | src/ui/forms/MainWindow.ui |
| test_serialized_feature.py | tests/test_serialized_feature.py |
