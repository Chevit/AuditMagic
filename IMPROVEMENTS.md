# AuditMagic Improvement Guide for Claude Code

> **Purpose**: This document provides step-by-step instructions for implementing improvements to the AuditMagic inventory management system. It is designed for Claude Code or other AI coding assistants to understand project context and execute improvements systematically.

## Table of Contents

- [Project Context](#project-context)
- [Critical Issues](#critical-issues)
- [High Priority Improvements](#high-priority-improvements)
- [Medium Priority Improvements](#medium-priority-improvements)
- [Low Priority Improvements](#low-priority-improvements)
- [Implementation Checklist](#implementation-checklist)

---

## Project Context

### Architecture Overview

**Tech Stack**: PyQt6, SQLAlchemy, SQLite, qt-material, Alembic
**Pattern**: MVC with Repository → Service → UI layers
**Codebase**: ~4,600 lines of Python
**Database**: SQLite with Alembic migrations
**Theme System**: Enum-based configuration (theme_config.py)

### Key Files

```
repositories.py      # Data access layer (CRUD operations)
services.py          # Business logic layer
models.py            # SQLAlchemy ORM models
ui_entities/         # PyQt6 UI components
  main_window.py     # Main application window
  inventory_list_view.py  # Custom QListView
theme_config.py      # Theme configuration enum
validators.py        # Input validation classes
db.py                # Database session management
config.py            # Application configuration
```

### Current Strengths

- Clean architectural separation
- Comprehensive transaction audit trail
- Good use of type hints and docstrings
- Signal-based UI architecture
- Enum-based theme system

### Known Issues

- No automated tests (pytest-qt in dev requirements but unused)
- Bug in `repositories.py` line 60 (undefined `notes` variable)
- No pagination for large datasets
- Limited input validation
- Generic error handling

---

## Critical Issues

### Issue #0: Code Cleanup and Consistency

**Priority**: CRITICAL | **Effort**: 1-2 days | **Impact**: Code maintainability, consistency, future Python compatibility

#### Overview

Before implementing new features, the codebase needs cleanup to ensure consistency, remove unused code, and fix deprecations. This establishes a clean foundation for future improvements.

#### Problems Identified

**1. Unused Files**
- `ui_entities/ListItem.py` - Never imported or used anywhere (48 lines)
- `ui_entities/main_window_model.py` - Never imported or used (48 lines)

**2. Inconsistent File Naming**
- `ListItem.py` uses PascalCase (should be `list_item.py` to match snake_case convention)
- All other files properly use snake_case naming

**3. Import Organization (PEP 8 Violation)**
Current imports don't follow PEP 8 ordering:
- Should be: Standard library → Third-party → Local application
- Currently: Mixed order throughout files

**4. Deprecated datetime.utcnow() Usage**
Multiple files use `datetime.utcnow()` which is deprecated in Python 3.12+:
- `models.py` lines 39, 40, 63, 82
- `repositories.py` line 536

**5. Documentation-Code Mismatch**
- `DIMENSION_GUIDE.md` documents `input_height=28, button_height=25`
- `theme_config.py` actually has `input_height=13, button_height=23`
- Need to sync documentation with actual values or fix the values

**6. Missing Project Files**
- No `.gitignore` file (important for VCS hygiene)
- No `.pre-commit-config.yaml` (mentioned in docs but missing)
- No `mypy.ini` or `setup.cfg` for type checking configuration

**7. Unpinned Dependencies**
- `requirements.txt` has no version pinning (e.g., `PyQt6>=6.7.0` instead of `PyQt6==6.7.1`)
- This can cause reproducibility issues

#### Solution: Systematic Cleanup

**Step 1: Remove Unused Files**

```bash
# Verify files are truly unused
grep -r "ListItem\|main_window_model" --include="*.py" . | grep -v ".venv\|.git"

# If confirmed unused, delete them
rm ui_entities/ListItem.py
rm ui_entities/main_window_model.py
```

**Step 2: Fix Import Organization**

Create a script or manually fix imports in all Python files to follow PEP 8:

Example for `ui_entities/main_window.py`:
```python
# Standard library imports
from typing import Optional

# Third-party imports
from PyQt6 import uic
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QActionGroup
from PyQt6.QtWidgets import QMainWindow, QMessageBox, QVBoxLayout, QWidget, QPushButton, QMenu

# Local application imports
from config import config
from db import init_database
from logger import logger
from services import InventoryService, SearchService, TransactionService
from styles import apply_button_style
from theme_manager import get_theme_manager
from ui_entities.add_item_dialog import AddItemDialog
from ui_entities.edit_item_dialog import EditItemDialog
from ui_entities.inventory_item import InventoryItem
from ui_entities.inventory_list_view import InventoryListView
from ui_entities.inventory_model import InventoryModel
from ui_entities.item_details_dialog import ItemDetailsDialog
from ui_entities.quantity_dialog import QuantityDialog
from ui_entities.search_widget import SearchWidget
from ui_entities.transactions_dialog import TransactionsDialog
from ui_entities.translations import tr
```

**Step 3: Fix Deprecated datetime Usage**

File: `models.py`
```python
# Change all occurrences from:
from datetime import datetime
created_at = Column(DateTime, default=datetime.utcnow)

# To:
from datetime import datetime, timezone
created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
```

File: `repositories.py` (line 536)
```python
# Change from:
existing.created_at = datetime.utcnow()

# To:
from datetime import timezone
existing.created_at = datetime.now(timezone.utc)
```

**Step 4: Sync Theme Documentation**

**Option A**: Update `theme_config.py` to match documentation
```python
# In theme_config.py, change:
dimensions=ThemeDimensions(
    input_height=28,  # Was 13, now matches docs
    button_height=25,  # Was 23, now matches docs
    # ... rest unchanged
)
```

**Option B**: Update `DIMENSION_GUIDE.md` to match code
```markdown
# Update all references from 28/25 to 13/23
| **input_height** | 13px | 13px | Input field height |
| **button_height** | 23px | 23px | Button height |
```

**Recommended**: Option A (update code to match docs, as 28/25 are more reasonable sizes)

**Step 5: Create .gitignore**

File: `.gitignore`
```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual Environment
.venv/
venv/
ENV/
env/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~
.DS_Store

# PyCharm
.idea/

# Testing
.pytest_cache/
.coverage
htmlcov/
*.cover

# Database
*.db
*.db-journal
inventory.db

# Logs
*.log
logs/

# Configuration
config.json
*.local.json

# Alembic
alembic/versions/*.pyc

# Qt
*.qmlc
*.jsc
.qmake.stash
```

**Step 6: Create Pre-commit Configuration**

File: `.pre-commit-config.yaml`
```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 24.3.0
    hooks:
      - id: black
        language_version: python3.11

  - repo: https://github.com/PyCQA/isort
    rev: 5.13.2
    hooks:
      - id: isort
        args: ["--profile", "black"]

  - repo: https://github.com/PyCQA/flake8
    rev: 7.0.0
    hooks:
      - id: flake8
        args: ["--max-line-length=88", "--extend-ignore=E203"]

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-merge-conflict
```

**Step 7: Pin Dependencies**

Update `requirements.txt` with specific versions:
```txt
# Core dependencies
PyQt6==6.7.1
SQLAlchemy==2.0.31
alembic==1.13.2
qt-material==2.14

# Development dependencies (move to requirements-dev.txt)
pytest==8.1.1
pytest-qt==4.4.0
pytest-cov==4.1.0
pytest-mock==3.12.0
mypy==1.9.0
black==24.3.0
isort==5.13.2
flake8==7.0.0
```

**Step 8: Create mypy Configuration**

File: `mypy.ini`
```ini
[mypy]
python_version = 3.11
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = False
disallow_incomplete_defs = False
check_untyped_defs = True
no_implicit_optional = True
warn_redundant_casts = True
warn_unused_ignores = True
warn_no_return = True
warn_unreachable = True
strict_equality = True

[mypy-PyQt6.*]
ignore_missing_imports = True

[mypy-qt_material.*]
ignore_missing_imports = True

[mypy-alembic.*]
ignore_missing_imports = True
```

**Step 9: Run Automated Cleanup**

```bash
# Install tools
pip install black isort flake8

# Format all Python files
black .

# Sort imports
isort .

# Check for issues (don't auto-fix yet)
flake8 . --max-line-length=88 --extend-ignore=E203

# Install pre-commit hooks
pip install pre-commit
pre-commit install
pre-commit run --all-files
```

#### Files to Create
- `.gitignore`
- `.pre-commit-config.yaml`
- `mypy.ini`

#### Files to Delete
- `ui_entities/ListItem.py`
- `ui_entities/main_window_model.py`

#### Files to Modify
- `models.py` (fix datetime.utcnow deprecation)
- `repositories.py` (fix datetime.utcnow deprecation)
- `theme_config.py` (sync with documentation: 28/25 instead of 13/23)
- `requirements.txt` (pin versions)
- All Python files (organize imports per PEP 8)

#### Testing After Cleanup

```bash
# Verify no import errors
python -c "import main"
python -c "from ui_entities import main_window"

# Verify app still runs
python main.py

# Run formatting checks
black --check .
isort --check .
flake8 .
```

#### Expected Impact

- **Consistency**: All files follow same naming and organization conventions
- **Maintainability**: Easier to navigate and understand codebase
- **Future-proofing**: Compatible with Python 3.12+
- **Reliability**: Pinned dependencies prevent surprise breakages
- **Quality**: Pre-commit hooks prevent future inconsistencies

---

### Issue #1: Fix ItemRepository.create() Bug

**Priority**: HIGH | **Effort**: 1 hour | **Impact**: Application crashes

#### Problem

File: `repositories.py`, Line 60
```python
# BUG: 'notes' parameter doesn't exist in function signature
notes=notes or tr("transaction.notes.initial"),
```

#### Solution

**Step 1**: Read the current implementation
```bash
Read repositories.py (lines 15-70)
```

**Step 2**: Fix the bug
```python
# Change line 60 from:
notes=notes or tr("transaction.notes.initial"),

# To:
notes=tr("transaction.notes.initial"),
```

**Step 3**: Test the fix
- Create a new item through the UI
- Verify transaction is created with correct notes

#### Files to Modify
- `repositories.py` (line 60)

---

### Issue #2: Add Automated Testing Infrastructure

**Priority**: HIGH | **Effort**: 2-3 weeks | **Impact**: Code reliability

#### Overview

Set up comprehensive testing framework with pytest and pytest-qt. Target 70% code coverage.

#### Implementation Steps

**Step 1: Create Test Directory Structure**

```bash
mkdir -p tests/unit
mkdir -p tests/integration
mkdir -p tests/ui
touch tests/__init__.py
touch tests/conftest.py
touch tests/unit/__init__.py
touch tests/integration/__init__.py
touch tests/ui/__init__.py
```

**Step 2: Create pytest Configuration**

File: `tests/conftest.py`
```python
"""Pytest configuration and fixtures."""
import pytest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db import init_database, session_scope
from models import Base


@pytest.fixture(scope="function")
def db_session():
    """Create in-memory database for testing."""
    init_database("sqlite:///:memory:")

    with session_scope() as session:
        yield session


@pytest.fixture(scope="function")
def sample_item_data():
    """Sample item data for testing."""
    return {
        "item_type": "Laptop",
        "sub_type": "ThinkPad X1",
        "quantity": 5,
        "serial_number": "ABC123",
        "details": "Test laptop for inventory"
    }
```

**Step 3: Write Repository Tests**

File: `tests/unit/test_repositories.py`
```python
"""Unit tests for repository layer."""
import pytest
from repositories import ItemRepository, TransactionRepository
from models import TransactionType


class TestItemRepository:
    """Tests for ItemRepository."""

    def test_create_item(self, db_session, sample_item_data):
        """Test creating a new item."""
        item = ItemRepository.create(**sample_item_data)

        assert item is not None
        assert item.id is not None
        assert item.item_type == sample_item_data["item_type"]
        assert item.quantity == sample_item_data["quantity"]

    def test_create_item_creates_transaction(self, db_session, sample_item_data):
        """Test that creating item creates initial transaction."""
        item = ItemRepository.create(**sample_item_data)
        transactions = TransactionRepository.get_by_item(item.id)

        assert len(transactions) == 1
        assert transactions[0].transaction_type == TransactionType.ADD
        assert transactions[0].quantity_change == sample_item_data["quantity"]

    def test_get_by_id(self, db_session, sample_item_data):
        """Test retrieving item by ID."""
        created = ItemRepository.create(**sample_item_data)
        retrieved = ItemRepository.get_by_id(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.item_type == created.item_type

    def test_get_by_id_not_found(self, db_session):
        """Test retrieving non-existent item."""
        result = ItemRepository.get_by_id(99999)
        assert result is None

    def test_add_quantity(self, db_session, sample_item_data):
        """Test adding quantity to existing item."""
        item = ItemRepository.create(**sample_item_data)
        original_qty = item.quantity

        updated = ItemRepository.add_quantity(item.id, 3, "Added stock")

        assert updated.quantity == original_qty + 3

    def test_remove_quantity(self, db_session, sample_item_data):
        """Test removing quantity from item."""
        item = ItemRepository.create(**sample_item_data)
        original_qty = item.quantity

        updated = ItemRepository.remove_quantity(item.id, 2, "Removed stock")

        assert updated.quantity == original_qty - 2

    def test_remove_quantity_insufficient(self, db_session, sample_item_data):
        """Test error when removing more than available."""
        item = ItemRepository.create(quantity=5, **{k: v for k, v in sample_item_data.items() if k != "quantity"})

        with pytest.raises(ValueError, match="Cannot remove"):
            ItemRepository.remove_quantity(item.id, 10, "Too much")

    def test_search(self, db_session):
        """Test searching items."""
        ItemRepository.create(item_type="Laptop", quantity=1)
        ItemRepository.create(item_type="Desktop", quantity=1)
        ItemRepository.create(item_type="Laptop Pro", quantity=1)

        results = ItemRepository.search("Laptop")

        assert len(results) == 2

    def test_delete(self, db_session, sample_item_data):
        """Test deleting an item."""
        item = ItemRepository.create(**sample_item_data)

        result = ItemRepository.delete(item.id)
        assert result is True

        retrieved = ItemRepository.get_by_id(item.id)
        assert retrieved is None
```

**Step 4: Write Service Tests**

File: `tests/unit/test_services.py`
```python
"""Unit tests for service layer."""
import pytest
from unittest.mock import Mock, patch
from services import InventoryService, SearchService
from ui_entities.inventory_item import InventoryItem


class TestInventoryService:
    """Tests for InventoryService."""

    @patch('services.ItemRepository.create')
    def test_create_item(self, mock_create):
        """Test creating item through service."""
        mock_item = Mock()
        mock_item.id = 1
        mock_item.item_type = "Test"
        mock_create.return_value = mock_item

        result = InventoryService.create_item(
            item_type="Test",
            quantity=5
        )

        assert mock_create.called
        assert isinstance(result, InventoryItem)

    @patch('services.ItemRepository.find_by_fields')
    @patch('services.ItemRepository.add_quantity')
    def test_create_or_merge_existing(self, mock_add, mock_find):
        """Test merging with existing item."""
        existing = Mock()
        existing.id = 1
        mock_find.return_value = existing

        updated = Mock()
        updated.quantity = 10
        mock_add.return_value = updated

        result, merged = InventoryService.create_or_merge_item(
            item_type="Test",
            quantity=5
        )

        assert merged is True
        assert mock_add.called
```

**Step 5: Write UI Tests (pytest-qt)**

File: `tests/ui/test_add_item_dialog.py`
```python
"""UI tests for AddItemDialog."""
import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication
from ui_entities.add_item_dialog import AddItemDialog


@pytest.fixture(scope="session")
def qapp():
    """Create QApplication instance."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def test_dialog_opens(qapp, qtbot):
    """Test that dialog can be created."""
    dialog = AddItemDialog()
    qtbot.addWidget(dialog)
    assert dialog is not None


def test_validation_empty_fields(qapp, qtbot):
    """Test validation rejects empty required fields."""
    dialog = AddItemDialog()
    qtbot.addWidget(dialog)

    # Try to accept with empty fields
    # Should show validation error
    pass  # TODO: Implement based on actual validation logic
```

**Step 6: Add pytest Configuration**

File: `pytest.ini`
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    -v
    --strict-markers
    --cov=.
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=70
markers =
    slow: marks tests as slow
    ui: marks tests as UI tests (require display)
```

**Step 7: Update requirements-dev.txt**

```txt
pytest>=7.4.0
pytest-qt>=4.2.0
pytest-cov>=4.1.0
pytest-mock>=3.11.0
```

**Step 8: Run Tests**

```bash
pytest tests/
pytest tests/ --cov
```

#### Files to Create
- `tests/conftest.py`
- `tests/unit/test_repositories.py`
- `tests/unit/test_services.py`
- `tests/ui/test_add_item_dialog.py`
- `pytest.ini`

#### Files to Modify
- `requirements-dev.txt` (add pytest-cov, pytest-mock)

---

## High Priority Improvements

### Issue #3: Performance Optimization

**Priority**: MEDIUM-HIGH | **Effort**: 1-2 weeks | **Impact**: Application responsiveness

#### Problem

- No pagination for large item lists
- No LIMIT clauses on search queries
- Potential performance issues with 1000+ items

#### Solution: Add Pagination

**Step 1: Update ItemRepository.get_all()**

File: `repositories.py`
```python
@staticmethod
def get_all(limit: int = None, offset: int = 0) -> List[Item]:
    """Get all items with optional pagination.

    Args:
        limit: Maximum number of items to return (None = all)
        offset: Number of items to skip

    Returns:
        List of Item instances.
    """
    with session_scope() as session:
        query = session.query(Item).order_by(Item.item_type, Item.sub_type)

        if limit is not None:
            query = query.limit(limit).offset(offset)

        items = query.all()
        return [_detach_item(item) for item in items]


@staticmethod
def get_count() -> int:
    """Get total count of items.

    Returns:
        Total number of items in database.
    """
    with session_scope() as session:
        return session.query(Item).count()
```

**Step 2: Update ItemRepository.search()**

File: `repositories.py`
```python
@staticmethod
def search(query: str, field: str = None, limit: int = 100) -> List[Item]:
    """Search items by query string with limit.

    Args:
        query: Search query string.
        field: Field to search in ('item_type', 'sub_type', 'details', or None for all).
        limit: Maximum number of results (default: 100).

    Returns:
        List of matching Item instances.
    """
    logger.debug(f"Repository: Searching items with query='{query}', field={field}, limit={limit}")
    with session_scope() as session:
        search_pattern = f"%{query}%"

        if field == "item_type":
            items = (
                session.query(Item)
                .filter(Item.item_type.ilike(search_pattern))
                .limit(limit)
                .all()
            )
        elif field == "sub_type":
            items = (
                session.query(Item)
                .filter(Item.sub_type.ilike(search_pattern))
                .limit(limit)
                .all()
            )
        elif field == "details":
            items = (
                session.query(Item)
                .filter(Item.details.ilike(search_pattern))
                .limit(limit)
                .all()
            )
        else:
            # Search in all fields
            items = (
                session.query(Item)
                .filter(
                    or_(
                        Item.item_type.ilike(search_pattern),
                        Item.sub_type.ilike(search_pattern),
                        Item.details.ilike(search_pattern),
                        Item.serial_number.ilike(search_pattern),  # Add serial number
                    )
                )
                .limit(limit)
                .all()
            )

        return [_detach_item(item) for item in items]
```

**Step 3: Add Database Indexes**

Create new Alembic migration:
```bash
alembic revision -m "add_performance_indexes"
```

File: `alembic/versions/XXXX_add_performance_indexes.py`
```python
"""add_performance_indexes

Revision ID: XXXX
"""
from alembic import op
import sqlalchemy as sa


def upgrade():
    # Add indexes for frequently queried columns
    op.create_index('idx_items_item_type', 'items', ['item_type'])
    op.create_index('idx_items_sub_type', 'items', ['sub_type'])
    op.create_index('idx_items_serial_number', 'items', ['serial_number'])
    op.create_index('idx_transactions_item_id', 'transactions', ['item_id'])
    op.create_index('idx_transactions_created_at', 'transactions', ['created_at'])


def downgrade():
    op.drop_index('idx_transactions_created_at', table_name='transactions')
    op.drop_index('idx_transactions_item_id', table_name='transactions')
    op.drop_index('idx_items_serial_number', table_name='items')
    op.drop_index('idx_items_sub_type', table_name='items')
    op.drop_index('idx_items_item_type', table_name='items')
```

**Step 4: Update Service Layer**

File: `services.py`
```python
@staticmethod
def get_all_items(limit: int = None, offset: int = 0) -> List[InventoryItem]:
    """Get all inventory items with pagination.

    Args:
        limit: Maximum number of items (None = all)
        offset: Number to skip

    Returns:
        List of InventoryItem instances.
    """
    db_items = ItemRepository.get_all(limit=limit, offset=offset)
    return [InventoryItem.from_db_model(item) for item in db_items]


@staticmethod
def get_item_count() -> int:
    """Get total count of items.

    Returns:
        Total number of items.
    """
    return ItemRepository.get_count()
```

#### Files to Modify
- `repositories.py` (add pagination parameters, add indexes)
- `services.py` (update to use pagination)
- Create new Alembic migration

---

### Issue #4: Input Validation Enhancement

**Priority**: MEDIUM | **Effort**: 1 week | **Impact**: Data quality

#### Solution: Enhanced Validation

**Step 1: Add Custom Exception Classes**

File: `exceptions.py` (new file)
```python
"""Custom exception classes for AuditMagic."""


class AuditMagicException(Exception):
    """Base exception for AuditMagic."""
    pass


class ValidationError(AuditMagicException):
    """Raised when validation fails."""

    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message
        super().__init__(f"{field}: {message}")


class ItemNotFoundException(AuditMagicException):
    """Raised when an item is not found."""

    def __init__(self, item_id: int):
        self.item_id = item_id
        super().__init__(f"Item with ID {item_id} not found")


class DuplicateItemWarning(AuditMagicException):
    """Warning for potential duplicate items."""

    def __init__(self, existing_item, similarity: float):
        self.existing_item = existing_item
        self.similarity = similarity
        super().__init__(f"Similar item found (similarity: {similarity:.0%})")


class InsufficientQuantityError(AuditMagicException):
    """Raised when trying to remove more quantity than available."""

    def __init__(self, requested: int, available: int):
        self.requested = requested
        self.available = available
        super().__init__(f"Cannot remove {requested} items. Only {available} available.")
```

**Step 2: Enhance validators.py**

File: `validators.py`
```python
# Add to existing file

def validate_item_type(value: str) -> Tuple[bool, str]:
    """Validate item type field.

    Args:
        value: Item type value

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not value or value.strip() == "":
        return (False, "Item type is required")

    if len(value.strip()) < 2:
        return (False, "Item type must be at least 2 characters")

    if len(value.strip()) > 255:
        return (False, "Item type must be at most 255 characters")

    return (True, "")


def validate_serial_number(value: str, allow_empty: bool = True) -> Tuple[bool, str]:
    """Validate serial number.

    Args:
        value: Serial number value
        allow_empty: Whether empty is allowed

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not allow_empty and (not value or value.strip() == ""):
        return (False, "Serial number is required")

    if value and len(value) > 255:
        return (False, "Serial number must be at most 255 characters")

    # Check format (alphanumeric and hyphens only)
    import re
    if value and not re.match(r'^[A-Za-z0-9\-]*$', value):
        return (False, "Serial number must contain only letters, numbers, and hyphens")

    return (True, "")


def check_duplicate_items(item_type: str, sub_type: str = "",
                          exclude_id: int = None) -> List[dict]:
    """Check for potential duplicate items using fuzzy matching.

    Args:
        item_type: Item type to check
        sub_type: Sub-type to check
        exclude_id: Item ID to exclude from check (for edits)

    Returns:
        List of similar items with similarity scores
    """
    from repositories import ItemRepository
    from difflib import SequenceMatcher

    all_items = ItemRepository.get_all()
    similar_items = []

    for item in all_items:
        if exclude_id and item.id == exclude_id:
            continue

        # Calculate similarity
        type_similarity = SequenceMatcher(None, item_type.lower(), item.item_type.lower()).ratio()
        subtype_similarity = SequenceMatcher(None, sub_type.lower(), item.sub_type.lower()).ratio()

        # Weighted average (type is more important)
        overall_similarity = (type_similarity * 0.7) + (subtype_similarity * 0.3)

        if overall_similarity > 0.8:  # 80% similar
            similar_items.append({
                'item': item,
                'similarity': overall_similarity
            })

    return sorted(similar_items, key=lambda x: x['similarity'], reverse=True)
```

**Step 3: Update Add Item Dialog**

File: `ui_entities/add_item_dialog.py`
```python
# Add validation and duplicate detection

def _validate_and_submit(self):
    """Validate inputs and check for duplicates before submitting."""
    # Existing validation...

    # Check for duplicates
    from validators import check_duplicate_items

    item_type = self.type_input.text().strip()
    sub_type = self.subtype_input.text().strip()

    similar_items = check_duplicate_items(item_type, sub_type)

    if similar_items:
        # Show warning dialog
        from PyQt6.QtWidgets import QMessageBox

        message = "Similar items found:\n\n"
        for sim in similar_items[:3]:  # Show top 3
            item = sim['item']
            message += f"• {item.item_type} - {item.sub_type} ({sim['similarity']:.0%} similar)\n"
        message += "\nDo you want to continue creating this item?"

        reply = QMessageBox.question(
            self,
            "Potential Duplicate",
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.No:
            return

    # Continue with item creation...
```

#### Files to Create
- `exceptions.py` (new file)

#### Files to Modify
- `validators.py` (add enhanced validation functions)
- `ui_entities/add_item_dialog.py` (add duplicate detection)
- `repositories.py` (use InsufficientQuantityError instead of ValueError)

---

### Issue #5: Error Handling Improvements

**Priority**: MEDIUM | **Effort**: 1 week | **Impact**: User experience

#### Solution: Centralized Error Handling

**Step 1: Update Services to Use Custom Exceptions**

File: `services.py`
```python
from exceptions import (
    ValidationError,
    ItemNotFoundException,
    InsufficientQuantityError
)

# Update methods to raise specific exceptions

@staticmethod
def get_item(item_id: int) -> InventoryItem:
    """Get an item by ID.

    Args:
        item_id: The item's ID.

    Returns:
        The InventoryItem.

    Raises:
        ItemNotFoundException: If item not found.
    """
    db_item = ItemRepository.get_by_id(item_id)
    if not db_item:
        raise ItemNotFoundException(item_id)
    return InventoryItem.from_db_model(db_item)
```

**Step 2: Create Error Handler Utility**

File: `ui_entities/error_handler.py` (new file)
```python
"""Centralized error handling for UI."""
from PyQt6.QtWidgets import QMessageBox, QWidget
from exceptions import (
    AuditMagicException,
    ValidationError,
    ItemNotFoundException,
    InsufficientQuantityError
)
from ui_entities.translations import tr
from logger import logger


def handle_error(parent: QWidget, error: Exception) -> None:
    """Display user-friendly error message.

    Args:
        parent: Parent widget for message box
        error: Exception to handle
    """
    logger.error(f"Error occurred: {type(error).__name__}: {str(error)}", exc_info=True)

    if isinstance(error, ValidationError):
        QMessageBox.warning(
            parent,
            tr("error.validation.title"),
            f"{tr('error.validation.message')}\n\n{error.message}",
            QMessageBox.StandardButton.Ok
        )

    elif isinstance(error, ItemNotFoundException):
        QMessageBox.critical(
            parent,
            tr("error.not_found.title"),
            tr("error.not_found.message").format(item_id=error.item_id),
            QMessageBox.StandardButton.Ok
        )

    elif isinstance(error, InsufficientQuantityError):
        QMessageBox.warning(
            parent,
            tr("error.quantity.title"),
            tr("error.quantity.message").format(
                requested=error.requested,
                available=error.available
            ),
            QMessageBox.StandardButton.Ok
        )

    elif isinstance(error, AuditMagicException):
        QMessageBox.critical(
            parent,
            tr("error.generic.title"),
            str(error),
            QMessageBox.StandardButton.Ok
        )

    else:
        # Unknown error
        QMessageBox.critical(
            parent,
            tr("error.unknown.title"),
            f"{tr('error.unknown.message')}\n\n{str(error)}",
            QMessageBox.StandardButton.Ok
        )


def handle_error_with_retry(parent: QWidget, error: Exception,
                            retry_callback) -> bool:
    """Display error with retry option.

    Args:
        parent: Parent widget
        error: Exception that occurred
        retry_callback: Function to call if user chooses retry

    Returns:
        True if user chose to retry
    """
    logger.error(f"Error occurred: {str(error)}", exc_info=True)

    reply = QMessageBox.question(
        parent,
        tr("error.retry.title"),
        f"{str(error)}\n\n{tr('error.retry.message')}",
        QMessageBox.StandardButton.Retry | QMessageBox.StandardButton.Cancel
    )

    if reply == QMessageBox.StandardButton.Retry:
        try:
            retry_callback()
            return True
        except Exception as retry_error:
            handle_error(parent, retry_error)
            return False

    return False
```

**Step 3: Add Error Translation Keys**

File: `ui_entities/translations.py`
```python
# Add to translations dictionary

"error.validation.title": {
    "uk": "Помилка валідації",
    "en": "Validation Error"
},
"error.validation.message": {
    "uk": "Будь ласка, виправте наступні помилки:",
    "en": "Please correct the following errors:"
},
"error.not_found.title": {
    "uk": "Товар не знайдено",
    "en": "Item Not Found"
},
"error.not_found.message": {
    "uk": "Товар з ID {item_id} не знайдено в базі даних.",
    "en": "Item with ID {item_id} was not found in the database."
},
"error.quantity.title": {
    "uk": "Недостатня кількість",
    "en": "Insufficient Quantity"
},
"error.quantity.message": {
    "uk": "Неможливо видалити {requested} одиниць. Доступно лише {available}.",
    "en": "Cannot remove {requested} items. Only {available} available."
},
```

**Step 4: Update UI to Use Error Handler**

File: `ui_entities/main_window.py`
```python
from ui_entities.error_handler import handle_error

def _on_delete_item(self, row: int, item: InventoryItem):
    """Handle item deletion with error handling."""
    try:
        # Existing deletion code...
        success = InventoryService.delete_item(item.id)
        if not success:
            raise ItemNotFoundException(item.id)
    except Exception as e:
        handle_error(self, e)
```

#### Files to Create
- `exceptions.py` (if not already created)
- `ui_entities/error_handler.py`

#### Files to Modify
- `services.py` (use custom exceptions)
- `ui_entities/translations.py` (add error messages)
- `ui_entities/main_window.py` (use error handler)
- All dialog files (use error handler)

---

## Medium Priority Improvements

### Issue #6: Database Backup & Export

**Priority**: MEDIUM | **Effort**: 2 weeks | **Impact**: Data protection

#### Implementation

**Step 1: Create Backup Service**

File: `backup_service.py` (new file)
```python
"""Database backup and restore functionality."""
import os
import shutil
from datetime import datetime
from pathlib import Path
from logger import logger, APP_DATA_DIR

BACKUP_DIR = os.path.join(APP_DATA_DIR, "backups")


def create_backup(source_db_path: str, backup_name: str = None) -> str:
    """Create database backup.

    Args:
        source_db_path: Path to source database file
        backup_name: Optional backup name (default: timestamp)

    Returns:
        Path to created backup file
    """
    os.makedirs(BACKUP_DIR, exist_ok=True)

    if backup_name is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"inventory_backup_{timestamp}.db"

    backup_path = os.path.join(BACKUP_DIR, backup_name)

    try:
        shutil.copy2(source_db_path, backup_path)
        logger.info(f"Database backed up to: {backup_path}")
        return backup_path
    except Exception as e:
        logger.error(f"Backup failed: {e}", exc_info=True)
        raise


def restore_backup(backup_path: str, target_db_path: str) -> bool:
    """Restore database from backup.

    Args:
        backup_path: Path to backup file
        target_db_path: Path to target database

    Returns:
        True if successful
    """
    try:
        # Create backup of current database first
        create_backup(target_db_path, "pre_restore_backup.db")

        # Restore from backup
        shutil.copy2(backup_path, target_db_path)
        logger.info(f"Database restored from: {backup_path}")
        return True
    except Exception as e:
        logger.error(f"Restore failed: {e}", exc_info=True)
        return False


def list_backups() -> list:
    """List all available backups.

    Returns:
        List of backup file info dicts
    """
    if not os.path.exists(BACKUP_DIR):
        return []

    backups = []
    for filename in os.listdir(BACKUP_DIR):
        if filename.endswith('.db'):
            path = os.path.join(BACKUP_DIR, filename)
            stat = os.stat(path)
            backups.append({
                'filename': filename,
                'path': path,
                'size': stat.st_size,
                'created': datetime.fromtimestamp(stat.st_ctime)
            })

    return sorted(backups, key=lambda x: x['created'], reverse=True)


def cleanup_old_backups(keep_count: int = 10) -> int:
    """Remove old backups, keeping only the most recent ones.

    Args:
        keep_count: Number of backups to keep

    Returns:
        Number of backups deleted
    """
    backups = list_backups()

    if len(backups) <= keep_count:
        return 0

    to_delete = backups[keep_count:]
    deleted = 0

    for backup in to_delete:
        try:
            os.remove(backup['path'])
            deleted += 1
            logger.info(f"Deleted old backup: {backup['filename']}")
        except Exception as e:
            logger.error(f"Failed to delete {backup['filename']}: {e}")

    return deleted
```

**Step 2: Create Export Service**

File: `export_service.py` (new file)
```python
"""Export functionality for inventory and transactions."""
import csv
from datetime import datetime
from typing import List
from repositories import ItemRepository, TransactionRepository


def export_inventory_to_csv(output_path: str) -> bool:
    """Export all inventory items to CSV.

    Args:
        output_path: Path to output CSV file

    Returns:
        True if successful
    """
    try:
        items = ItemRepository.get_all()

        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            # Header
            writer.writerow([
                'ID', 'Item Type', 'Sub Type', 'Quantity',
                'Serial Number', 'Details', 'Created At', 'Updated At'
            ])

            # Data
            for item in items:
                writer.writerow([
                    item.id,
                    item.item_type,
                    item.sub_type,
                    item.quantity,
                    item.serial_number,
                    item.details,
                    item.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    item.updated_at.strftime('%Y-%m-%d %H:%M:%S')
                ])

        return True
    except Exception as e:
        logger.error(f"Export failed: {e}", exc_info=True)
        return False


def export_transactions_to_csv(output_path: str, item_id: int = None) -> bool:
    """Export transactions to CSV.

    Args:
        output_path: Path to output CSV file
        item_id: Optional item ID to filter by

    Returns:
        True if successful
    """
    try:
        if item_id:
            transactions = TransactionRepository.get_by_item(item_id)
        else:
            transactions = TransactionRepository.get_recent(limit=10000)

        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            # Header
            writer.writerow([
                'ID', 'Item ID', 'Type', 'Quantity Change',
                'Quantity Before', 'Quantity After', 'Notes', 'Created At'
            ])

            # Data
            for trans in transactions:
                writer.writerow([
                    trans.id,
                    trans.item_id,
                    trans.transaction_type.value,
                    trans.quantity_change,
                    trans.quantity_before,
                    trans.quantity_after,
                    trans.notes,
                    trans.created_at.strftime('%Y-%m-%d %H:%M:%S')
                ])

        return True
    except Exception as e:
        logger.error(f"Export failed: {e}", exc_info=True)
        return False
```

**Step 3: Update db.py to Backup Before Migrations**

File: `db.py`
```python
def run_migrations() -> None:
    """Run database migrations with automatic backup."""
    from alembic.config import Config
    from alembic import command
    from backup_service import create_backup

    logger.info("Running database migrations...")

    # Create backup before migration
    if os.path.exists(DATABASE_PATH):
        try:
            backup_path = create_backup(DATABASE_PATH, "pre_migration_backup.db")
            logger.info(f"Pre-migration backup created: {backup_path}")
        except Exception as e:
            logger.warning(f"Failed to create pre-migration backup: {e}")

    alembic_cfg = Config(os.path.join(os.path.dirname(__file__), "alembic.ini"))

    try:
        command.upgrade(alembic_cfg, "head")
        logger.info("Database migrations completed successfully")
    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        raise
```

**Step 4: Add Backup/Export Menu Items**

File: `ui_entities/main_window.py`
```python
def _setup_file_menu(self):
    """Set up File menu with backup and export options."""
    menu_bar = self.menuBar()
    file_menu = menu_bar.addMenu(tr("menu.file"))

    # Backup submenu
    backup_menu = file_menu.addMenu(tr("menu.backup"))

    create_backup_action = QAction(tr("menu.backup.create"), self)
    create_backup_action.triggered.connect(self._on_create_backup)
    backup_menu.addAction(create_backup_action)

    restore_backup_action = QAction(tr("menu.backup.restore"), self)
    restore_backup_action.triggered.connect(self._on_restore_backup)
    backup_menu.addAction(restore_backup_action)

    # Export submenu
    export_menu = file_menu.addMenu(tr("menu.export"))

    export_inventory_action = QAction(tr("menu.export.inventory"), self)
    export_inventory_action.triggered.connect(self._on_export_inventory)
    export_menu.addAction(export_inventory_action)

    export_transactions_action = QAction(tr("menu.export.transactions"), self)
    export_transactions_action.triggered.connect(self._on_export_transactions)
    export_menu.addAction(export_transactions_action)
```

#### Files to Create
- `backup_service.py`
- `export_service.py`

#### Files to Modify
- `db.py` (add backup before migrations)
- `ui_entities/main_window.py` (add menu items and handlers)
- `ui_entities/translations.py` (add translation keys)

---

## Implementation Checklist

### Phase 0: Code Cleanup (1-2 days) ⚡ START HERE

- [ ] **Delete unused files** (ListItem.py, main_window_model.py)
- [ ] **Fix deprecated datetime.utcnow()** (models.py, repositories.py)
- [ ] **Sync theme dimensions** (theme_config.py: 13→28, 23→25)
- [ ] **Create .gitignore** (standard Python/PyQt6 ignores)
- [ ] **Create .pre-commit-config.yaml** (black, isort, flake8)
- [ ] **Create mypy.ini** (type checking configuration)
- [ ] **Pin dependencies** (requirements.txt with exact versions)
- [ ] **Organize imports** (PEP 8: stdlib → third-party → local)
- [ ] **Run black formatter** on entire codebase
- [ ] **Run isort** to sort all imports
- [ ] **Install and run pre-commit hooks**
- [ ] **Test application still works** after cleanup

### Phase 1: Critical Fixes (1-2 weeks)

- [ ] **Fix ItemRepository.create() bug** (repositories.py line 60)
- [ ] **Create test directory structure** (tests/, conftest.py)
- [ ] **Write repository unit tests** (test_repositories.py)
- [ ] **Write service unit tests** (test_services.py)
- [ ] **Add pytest configuration** (pytest.ini)
- [ ] **Run tests and achieve 70% coverage**
- [ ] **Create custom exception classes** (exceptions.py)

### Phase 2: Performance & Validation (2-3 weeks)

- [ ] **Add pagination to repositories** (get_all, search methods)
- [ ] **Create database indexes migration**
- [ ] **Update services for pagination**
- [ ] **Enhance validators.py** (add business validation)
- [ ] **Add duplicate detection** (check_duplicate_items)
- [ ] **Create error handler utility** (error_handler.py)
- [ ] **Update UI to use error handler**
- [ ] **Add error translation keys**

### Phase 3: Features & UX (3-4 weeks)

- [ ] **Create backup service** (backup_service.py)
- [ ] **Create export service** (export_service.py)
- [ ] **Add backup before migrations** (db.py)
- [ ] **Add File menu with backup/export** (main_window.py)
- [ ] **Add keyboard shortcuts** (Ctrl+N, Ctrl+F, etc.)
- [ ] **Implement advanced search dialog**
- [ ] **Add serial_number to search**
- [ ] **Add quantity range filters**
- [ ] **Implement column sorting**

### Phase 4: Polish & Documentation (2-3 weeks)

- [ ] **Set up pre-commit hooks** (.pre-commit-config.yaml)
- [ ] **Add GitHub Actions workflow** (.github/workflows/test.yml)
- [ ] **Configure mypy** (mypy.ini)
- [ ] **Create user manual** (docs/user_manual.md)
- [ ] **Add inline tooltips**
- [ ] **Generate API docs with Sphinx**

---

## Testing Guidelines

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov

# Run specific test file
pytest tests/unit/test_repositories.py

# Run tests with verbose output
pytest -v

# Run only fast tests (skip slow UI tests)
pytest -m "not slow"
```

### Writing New Tests

1. **Repository tests**: Use in-memory SQLite database
2. **Service tests**: Mock repository layer
3. **UI tests**: Use pytest-qt fixtures
4. **Integration tests**: Test full stack with test database

### Test Coverage Goals

- **Repository layer**: 90%+ coverage
- **Service layer**: 85%+ coverage
- **UI layer**: 60%+ coverage (focus on business logic)
- **Overall**: 70%+ coverage

---

## Code Style Guidelines

### Python Style

- Follow PEP 8
- Use Black formatter (line length: 88)
- Type hints on all function signatures
- Docstrings for all public functions and classes
- Use f-strings for formatting

### Git Commit Messages

```
type(scope): short description

Longer description if needed

Fixes #123
```

Types: `fix`, `feat`, `refactor`, `test`, `docs`, `chore`

### Example Commits

```
fix(repositories): fix undefined notes variable in create()

The create() method referenced a 'notes' parameter that doesn't
exist in the function signature. Changed to use translation directly.

Fixes #2

feat(testing): add unit tests for ItemRepository

Added comprehensive unit tests for ItemRepository covering:
- create, get, update, delete operations
- add/remove quantity with transaction creation
- search functionality
- error cases

Achieves 92% coverage of repositories.py

refactor(validation): add custom exception classes

Created exceptions.py with custom exceptions:
- ValidationError
- ItemNotFoundException
- InsufficientQuantityError
- DuplicateItemWarning

Updated services to raise specific exceptions instead of generic ones.
```

---

## Notes for Claude Code

### When Implementing Changes

1. **Always read the file first** before making changes
2. **Run existing tests** before modifying code
3. **Add tests for new functionality** before implementing
4. **Update CLAUDE.md** if architecture changes
5. **Check for breaking changes** in existing UI
6. **Test manually** after automated tests pass
7. **Update translations** if adding new UI text
8. **Run Black formatter** before committing

### Common Pitfalls to Avoid

- Don't modify `theme_config.py` without understanding enum structure
- Don't break existing signal connections in UI
- Always use `session_scope()` context manager for database operations
- Always detach SQLAlchemy objects before returning from repositories
- Don't forget to update both Light and Dark themes
- Test with non-empty database (not just empty state)

### Getting Help

- Review `CLAUDE.md` for project conventions
- Check `DIMENSION_GUIDE.md` for theme sizing
- See `THEME_SYSTEM_REFACTOR.md` for theme architecture
- Look at existing code patterns before adding new features

---

## Summary

This guide provides comprehensive instructions for improving the AuditMagic application. Start with the critical issues (bug fix and testing), then proceed to performance optimizations, and finally add new features. Each improvement includes detailed implementation steps, code examples, and files to modify.

The total estimated implementation time is 10-14 weeks for a single developer working alone, or 6-8 weeks for a small team working in parallel.

**Priority order**:
1. Fix the repository bug (1 hour)
2. Add automated testing (2-3 weeks)
3. Performance optimization (1-2 weeks)
4. Enhanced validation (1 week)
5. Error handling (1 week)
6. Backup & export (2 weeks)
7. Additional features as needed
