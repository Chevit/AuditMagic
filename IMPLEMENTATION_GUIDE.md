# AuditMagic Improvements - Implementation Guide for Claude Code

## Overview
This guide provides step-by-step instructions to improve the AuditMagic inventory management application. Follow these steps in order for the best results.

---

## Phase 1: Foundation & Infrastructure (Day 1)

### Step 1: Add Logging System (Priority: CRITICAL)

**Objective:** Implement comprehensive logging to track errors and application behavior.

**Files to create:**
- `logger.py`

**Files to modify:**
- `main.py`
- `db.py`
- `services.py`
- `repositories.py`

**Instructions:**

1. Create `logger.py` in the project root:
```python
"""Centralized logging configuration for AuditMagic."""
import logging
import os
from datetime import datetime

# Create logs directory in app data
APP_DATA_DIR = os.path.join(os.path.expanduser("~"), ".audit_magic")
LOGS_DIR = os.path.join(APP_DATA_DIR, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

# Log file with timestamp
LOG_FILE = os.path.join(LOGS_DIR, f"audit_magic_{datetime.now().strftime('%Y%m%d')}.log")

def setup_logger(name: str = "AuditMagic") -> logging.Logger:
    """Set up and return a logger instance.
    
    Args:
        name: Logger name (default: "AuditMagic")
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Only configure if not already configured
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        
        # File handler - detailed logs
        file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        
        # Console handler - important messages only
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        console_formatter = logging.Formatter('%(levelname)s - %(message)s')
        console_handler.setFormatter(console_formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
    
    return logger

# Create default logger
logger = setup_logger()
```

2. Update `main.py` to initialize logging:
```python
import sys
from PyQt6.QtWidgets import QApplication
from ui_entities.main_window import MainWindow
from logger import logger

def main():
    logger.info("=" * 80)
    logger.info("AuditMagic Application Starting")
    logger.info("=" * 80)
    
    try:
        app = QApplication(sys.argv)
        logger.info("QApplication created successfully")
        
        window = MainWindow()
        logger.info("MainWindow created successfully")
        
        window.show()
        logger.info("MainWindow displayed")
        
        exit_code = app.exec()
        logger.info(f"Application exited with code: {exit_code}")
        return exit_code
        
    except Exception as e:
        logger.exception("Critical error during application startup")
        raise

if __name__ == "__main__":
    sys.exit(main())
```

3. Add logging to `db.py` for database operations:
```python
# At the top of db.py
from logger import logger

# In init_database function, add:
def init_database(db_url: str = None) -> None:
    global engine, SessionLocal
    
    if db_url is None:
        db_url = DATABASE_URL
        os.makedirs(APP_DATA_DIR, exist_ok=True)
        logger.info(f"Database directory created/verified: {APP_DATA_DIR}")
    elif db_url == ":memory:":
        db_url = "sqlite:///:memory:"
        logger.info("Using in-memory database")
    
    logger.info(f"Initializing database with URL: {db_url}")
    
    engine = create_engine(...)
    SessionLocal = sessionmaker(...)
    Base.metadata.create_all(bind=engine)
    
    logger.info("Database initialized successfully")

# In session_scope, add error logging:
@contextmanager
def session_scope() -> Generator[Session, None, None]:
    session = get_session()
    try:
        yield session
        session.commit()
        logger.debug("Database transaction committed successfully")
    except Exception as e:
        session.rollback()
        logger.error(f"Database transaction failed: {str(e)}", exc_info=True)
        raise
    finally:
        session.close()
```

4. Add logging to critical service operations in `services.py`:
```python
from logger import logger

# In InventoryService methods:
@staticmethod
def create_item(...) -> InventoryItem:
    logger.info(f"Creating new item: type='{item_type}', quantity={quantity}")
    try:
        db_item = ItemRepository.create(...)
        logger.info(f"Item created successfully: id={db_item.id}")
        return InventoryItem.from_db_model(db_item)
    except Exception as e:
        logger.error(f"Failed to create item: {str(e)}", exc_info=True)
        raise

@staticmethod
def delete_item(item_id: int) -> bool:
    logger.info(f"Attempting to delete item: id={item_id}")
    result = ItemRepository.delete(item_id)
    if result:
        logger.info(f"Item deleted successfully: id={item_id}")
    else:
        logger.warning(f"Failed to delete item (not found): id={item_id}")
    return result
```

**Testing:**
- Run the application
- Check that `~/.audit_magic/logs/` directory is created
- Verify log file exists with today's date
- Perform various operations (add, edit, delete items)
- Open log file and verify entries are being written

---

### Step 2: Add Configuration Management (Priority: CRITICAL)

**Objective:** Create a configuration system for user preferences and app settings.

**Files to create:**
- `config.py`

**Files to modify:**
- `main.py`
- `ui_entities/main_window.py`
- `ui_entities/translations.py`

**Instructions:**

1. Create `config.py`:
```python
"""Application configuration management."""
import json
import os
from typing import Dict, Any, Optional
from pathlib import Path
from logger import logger

APP_DATA_DIR = os.path.join(os.path.expanduser("~"), ".audit_magic")
CONFIG_FILE = os.path.join(APP_DATA_DIR, "config.json")

DEFAULT_CONFIG = {
    "language": "uk",  # Ukrainian by default
    "theme": "default",
    "window": {
        "geometry": None,  # Will store window size/position
        "maximized": False
    },
    "search": {
        "save_history": True,
        "history_limit": 5,
        "autocomplete_enabled": True
    },
    "database": {
        "backup_on_startup": False,
        "auto_backup_days": 7
    },
    "ui": {
        "show_tooltips": True,
        "confirm_delete": True,
        "date_format": "dd.MM.yyyy",
        "time_format": "HH:mm:ss"
    }
}

class Config:
    """Configuration manager for application settings."""
    
    def __init__(self):
        """Initialize configuration, creating default if needed."""
        self._config: Dict[str, Any] = {}
        self.load()
    
    def load(self) -> None:
        """Load configuration from file or create default."""
        os.makedirs(APP_DATA_DIR, exist_ok=True)
        
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                # Merge with defaults to ensure all keys exist
                self._config = self._merge_configs(DEFAULT_CONFIG, loaded_config)
                logger.info(f"Configuration loaded from: {CONFIG_FILE}")
            except Exception as e:
                logger.error(f"Failed to load config, using defaults: {e}")
                self._config = DEFAULT_CONFIG.copy()
        else:
            self._config = DEFAULT_CONFIG.copy()
            self.save()
            logger.info(f"Default configuration created at: {CONFIG_FILE}")
    
    def save(self) -> None:
        """Save current configuration to file."""
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
            logger.info("Configuration saved successfully")
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by dot-notation key.
        
        Args:
            key: Configuration key (e.g., 'window.geometry', 'language')
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any, save: bool = True) -> None:
        """Set configuration value by dot-notation key.
        
        Args:
            key: Configuration key (e.g., 'window.geometry')
            value: Value to set
            save: Whether to save immediately (default: True)
        """
        keys = key.split('.')
        config = self._config
        
        # Navigate to the parent of the target key
        for k in keys[:-1]:
            if k not in config or not isinstance(config[k], dict):
                config[k] = {}
            config = config[k]
        
        # Set the value
        config[keys[-1]] = value
        logger.debug(f"Config set: {key} = {value}")
        
        if save:
            self.save()
    
    def reset(self) -> None:
        """Reset configuration to defaults."""
        self._config = DEFAULT_CONFIG.copy()
        self.save()
        logger.info("Configuration reset to defaults")
    
    @staticmethod
    def _merge_configs(default: Dict, loaded: Dict) -> Dict:
        """Recursively merge loaded config with defaults."""
        result = default.copy()
        for key, value in loaded.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = Config._merge_configs(result[key], value)
            else:
                result[key] = value
        return result

# Global config instance
config = Config()
```

2. Update `ui_entities/main_window.py` to use config for window geometry:
```python
from config import config

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("ui/MainWindow.ui", self)
        
        # Initialize database
        init_database()
        
        # Restore window geometry from config
        self._restore_window_state()
        
        # ... rest of initialization
    
    def _restore_window_state(self):
        """Restore window size and position from config."""
        geometry = config.get('window.geometry')
        if geometry:
            self.restoreGeometry(bytes.fromhex(geometry))
            logger.debug("Window geometry restored from config")
        
        if config.get('window.maximized', False):
            self.showMaximized()
            logger.debug("Window maximized from config")
    
    def closeEvent(self, event):
        """Save window state before closing."""
        # Save window geometry
        config.set('window.geometry', self.saveGeometry().toHex().data().decode())
        config.set('window.maximized', self.isMaximized())
        logger.info("Window state saved to config")
        
        event.accept()
```

3. Update `ui_entities/translations.py` to use config for language:
```python
from config import config

# Initialize language from config
_current_language: Language = Language(config.get('language', 'uk'))

def set_language(language: Language) -> None:
    """Set the current application language and save to config."""
    global _current_language
    _current_language = language
    config.set('language', language.value)
    logger.info(f"Language changed to: {language.value}")
```

**Testing:**
- Run application, resize/move window, close it
- Check `~/.audit_magic/config.json` exists
- Verify window geometry is saved
- Run application again - window should restore to previous position/size
- Change language and verify it persists after restart

---

### Step 3: Add Database Migrations (Priority: CRITICAL)

**Objective:** Implement Alembic for database schema versioning.

**Files to create:**
- `alembic.ini`
- `alembic/env.py`
- `alembic/versions/` (directory)

**Instructions:**

1. Install Alembic:
```bash
pip install alembic
```

2. Update `requirements.txt`:
```txt
PyQt6>=6.0.0
SQLAlchemy>=2.0.0
alembic>=1.13.0
```

3. Initialize Alembic:
```bash
cd C:\Users\chevi\PycharmProjects\AuditMagic
alembic init alembic
```

4. Update `alembic.ini` - change the sqlalchemy.url line:
```ini
# Remove or comment out this line:
# sqlalchemy.url = driver://user:pass@localhost/dbname

# We'll set it programmatically in env.py instead
```

5. Update `alembic/env.py`:
```python
from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from models import Base
from db import DATABASE_URL

# this is the Alembic Config object
config = context.config

# Set the database URL
config.set_main_option('sqlalchemy.url', DATABASE_URL)

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import your models' Base for autogenerate support
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

6. Create initial migration:
```bash
alembic revision --autogenerate -m "Initial schema"
```

7. Apply migration:
```bash
alembic upgrade head
```

8. Add migration helper to `db.py`:
```python
def run_migrations() -> None:
    """Run database migrations using Alembic."""
    from alembic.config import Config
    from alembic import command
    import os
    
    logger.info("Running database migrations...")
    
    # Path to alembic.ini
    alembic_cfg = Config(os.path.join(os.path.dirname(__file__), "alembic.ini"))
    
    try:
        command.upgrade(alembic_cfg, "head")
        logger.info("Database migrations completed successfully")
    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        raise
```

9. Update `main.py` to run migrations on startup:
```python
from db import init_database, run_migrations

def main():
    logger.info("=" * 80)
    logger.info("AuditMagic Application Starting")
    logger.info("=" * 80)
    
    try:
        # Initialize database
        init_database()
        
        # Run migrations
        run_migrations()
        
        # Start application
        app = QApplication(sys.argv)
        # ... rest of code
```

**Future schema changes:**
When you need to modify the database schema:
```bash
# 1. Modify models.py
# 2. Create migration:
alembic revision --autogenerate -m "Add new_column to items"
# 3. Review the generated migration file in alembic/versions/
# 4. Apply it:
alembic upgrade head
```

**Testing:**
- Delete existing database: `~/.audit_magic/inventory.db`
- Run application - should create database and run migrations
- Check alembic version table exists: `alembic_version`
- Add test data
- Create a new migration (add a test column to models.py)
- Run migration and verify data is preserved

---

## Phase 2: Code Quality & Validation (Day 2)

### Step 4: Add Input Validation (Priority: HIGH)

**Objective:** Improve form validation with proper validators and error handling.

**Files to create:**
- `validators.py`

**Files to modify:**
- `ui_entities/add_item_dialog.py`
- `ui_entities/quantity_dialog.py`

**Instructions:**

1. Create `validators.py`:
```python
"""Input validators for form fields."""
from PyQt6.QtGui import QValidator, QIntValidator, QRegularExpressionValidator
from PyQt6.QtCore import QRegularExpression
from typing import Tuple

class PositiveIntValidator(QIntValidator):
    """Validator for positive integers only."""
    
    def __init__(self, minimum: int = 1, maximum: int = 999999, parent=None):
        super().__init__(minimum, maximum, parent)
    
    def validate(self, input_str: str, pos: int) -> Tuple[QValidator.State, str, int]:
        if input_str == "":
            return (QValidator.State.Intermediate, input_str, pos)
        
        state, validated_str, new_pos = super().validate(input_str, pos)
        
        if state == QValidator.State.Acceptable:
            try:
                value = int(validated_str)
                if value < 1:
                    return (QValidator.State.Invalid, validated_str, new_pos)
            except ValueError:
                return (QValidator.State.Invalid, validated_str, new_pos)
        
        return (state, validated_str, new_pos)

class AlphanumericValidator(QRegularExpressionValidator):
    """Validator for alphanumeric strings with limited special characters."""
    
    def __init__(self, parent=None):
        # Allow letters, numbers, spaces, hyphens, underscores
        pattern = QRegularExpression(r"^[A-Za-z0-9\s\-_]*$")
        super().__init__(pattern, parent)

class SerialNumberValidator(QRegularExpressionValidator):
    """Validator for serial numbers."""
    
    def __init__(self, parent=None):
        # Allow letters, numbers, hyphens, no spaces
        pattern = QRegularExpression(r"^[A-Za-z0-9\-]*$")
        super().__init__(pattern, parent)

class ItemTypeValidator(QRegularExpressionValidator):
    """Validator for item type field."""
    
    def __init__(self, parent=None):
        # Allow letters, numbers, spaces, basic punctuation
        # Minimum length will be checked separately
        pattern = QRegularExpression(r"^[A-Za-zА-Яа-яІіЇїЄєҐґ0-9\s\-_.,/]*$")
        super().__init__(pattern, parent)

def validate_required_field(value: str, field_name: str) -> Tuple[bool, str]:
    """Validate that a required field is not empty.
    
    Args:
        value: Field value
        field_name: Name of field for error message
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not value or value.strip() == "":
        return (False, f"{field_name} is required")
    return (True, "")

def validate_positive_integer(value: str, field_name: str, 
                             minimum: int = 1, maximum: int = 999999) -> Tuple[bool, str]:
    """Validate that a value is a positive integer.
    
    Args:
        value: Value to validate
        field_name: Name of field for error message
        minimum: Minimum allowed value (default: 1)
        maximum: Maximum allowed value (default: 999999)
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        int_value = int(value)
        if int_value < minimum:
            return (False, f"{field_name} must be at least {minimum}")
        if int_value > maximum:
            return (False, f"{field_name} must be at most {maximum}")
        return (True, "")
    except (ValueError, TypeError):
        return (False, f"{field_name} must be a valid number")

def validate_length(value: str, field_name: str, 
                   min_length: int = 0, max_length: int = 255) -> Tuple[bool, str]:
    """Validate string length.
    
    Args:
        value: Value to validate
        field_name: Name of field for error message
        min_length: Minimum length (default: 0)
        max_length: Maximum length (default: 255)
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    length = len(value.strip()) if value else 0
    
    if length < min_length:
        return (False, f"{field_name} must be at least {min_length} characters")
    if length > max_length:
        return (False, f"{field_name} must be at most {max_length} characters")
    
    return (True, "")
```

2. Update `ui_entities/add_item_dialog.py` to use validators:
```python
from validators import (
    ItemTypeValidator, SerialNumberValidator, PositiveIntValidator,
    validate_required_field, validate_positive_integer, validate_length
)
from logger import logger

class AddItemDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        uic.loadUi("ui/AddItemDialog.ui", self)
        
        # Set up validators
        self._setup_validators()
        
        # ... rest of init
    
    def _setup_validators(self):
        """Set up input validators for form fields."""
        # Item type - required, letters/numbers/spaces
        self.typeLineEdit.setValidator(ItemTypeValidator(self))
        
        # Serial number - alphanumeric with hyphens
        if hasattr(self, 'serialNumberLineEdit'):
            self.serialNumberLineEdit.setValidator(SerialNumberValidator(self))
        
        # Quantity - positive integers only
        if hasattr(self, 'quantitySpinBox'):
            self.quantitySpinBox.setMinimum(1)
            self.quantitySpinBox.setMaximum(999999)
        
        logger.debug("Form validators configured")
    
    def accept(self):
        """Validate form before accepting."""
        errors = []
        
        # Validate item type
        item_type = self.typeLineEdit.text().strip()
        valid, error = validate_required_field(item_type, "Item type")
        if not valid:
            errors.append(error)
        else:
            valid, error = validate_length(item_type, "Item type", min_length=2, max_length=255)
            if not valid:
                errors.append(error)
        
        # Validate quantity
        quantity = self.quantitySpinBox.value()
        valid, error = validate_positive_integer(str(quantity), "Quantity", minimum=1)
        if not valid:
            errors.append(error)
        
        # Validate serial number length if provided
        if hasattr(self, 'serialNumberLineEdit'):
            serial = self.serialNumberLineEdit.text().strip()
            if serial:
                valid, error = validate_length(serial, "Serial number", max_length=255)
                if not valid:
                    errors.append(error)
        
        # Validate notes length if provided
        if hasattr(self, 'notesTextEdit'):
            notes = self.notesTextEdit.toPlainText().strip()
            if notes:
                valid, error = validate_length(notes, "Notes", max_length=1000)
                if not valid:
                    errors.append(error)
        
        # Show errors if any
        if errors:
            from ui_entities.translations import tr
            QMessageBox.warning(
                self,
                tr("message.validation_error"),
                tr("message.fix_errors") + "\n\n" + "\n".join(f"• {e}" for e in errors)
            )
            logger.warning(f"Form validation failed: {errors}")
            return
        
        logger.info("Form validation passed")
        super().accept()
```

3. Handle empty QSpinBox issue:
```python
# In quantity_dialog.py or add_item_dialog.py

class QuantityDialog(QDialog):
    def __init__(self, ...):
        super().__init__(parent)
        # ... setup
        
        # Connect to textChanged to handle empty field
        self.quantitySpinBox.lineEdit().textChanged.connect(self._on_quantity_text_changed)
    
    def _on_quantity_text_changed(self, text: str):
        """Handle when quantity field text changes, including when cleared."""
        if text == "":
            # Field is empty - could show warning or set placeholder
            logger.debug("Quantity field cleared")
            # Optionally set a minimum value when user tries to clear
            # self.quantitySpinBox.setValue(1)
        else:
            logger.debug(f"Quantity text changed to: {text}")
```

**Testing:**
- Try entering invalid characters in item type field
- Try entering negative numbers in quantity
- Try clearing quantity field (test your QSpinBox fix)
- Try entering very long text in notes
- Verify error messages show for all validation failures

---

### Step 5: Add Comprehensive Testing (Priority: HIGH)

**Objective:** Create test suite for repositories, services, and models.

**Files to create:**
- `tests/__init__.py`
- `tests/conftest.py`
- `tests/test_models.py`
- `tests/test_repositories.py`
- `tests/test_services.py`
- `requirements-dev.txt`

**Instructions:**

1. Install testing dependencies:
```bash
pip install pytest pytest-qt pytest-cov
```

2. Create `requirements-dev.txt`:
```txt
pytest==8.1.1
pytest-qt==4.4.0
pytest-cov==5.0.0
black==24.4.2
mypy==1.10.0
```

3. Create `tests/conftest.py`:
```python
"""Pytest configuration and fixtures."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Item, Transaction, TransactionType
from db import init_database

@pytest.fixture(scope="function")
def db_session():
    """Create an in-memory database session for testing."""
    # Use in-memory SQLite database
    init_database("sqlite:///:memory:")
    
    from db import get_session
    session = get_session()
    
    yield session
    
    session.close()

@pytest.fixture
def sample_item(db_session):
    """Create a sample item for testing."""
    item = Item(
        item_type="Laptop",
        sub_type="Dell XPS",
        quantity=5,
        serial_number="SN12345",
        notes="Test laptop"
    )
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)
    return item

@pytest.fixture
def sample_items(db_session):
    """Create multiple sample items for testing."""
    items = [
        Item(item_type="Laptop", sub_type="Dell", quantity=5, serial_number="SN001"),
        Item(item_type="Mouse", sub_type="Logitech", quantity=10, serial_number="SN002"),
        Item(item_type="Keyboard", sub_type="Mechanical", quantity=3, serial_number="SN003"),
    ]
    for item in items:
        db_session.add(item)
    db_session.commit()
    
    for item in items:
        db_session.refresh(item)
    
    return items
```

4. Create `tests/test_models.py`:
```python
"""Tests for database models."""
import pytest
from datetime import datetime
from models import Item, Transaction, TransactionType

def test_item_creation():
    """Test creating an Item instance."""
    item = Item(
        item_type="Laptop",
        sub_type="Dell",
        quantity=5,
        serial_number="SN123",
        notes="Test item"
    )
    
    assert item.item_type == "Laptop"
    assert item.sub_type == "Dell"
    assert item.quantity == 5
    assert item.serial_number == "SN123"
    assert item.notes == "Test item"

def test_item_default_values():
    """Test Item default values."""
    item = Item(item_type="Monitor", quantity=1)
    
    assert item.quantity == 1
    assert item.sub_type is None
    assert item.serial_number is None
    assert item.notes is None

def test_item_repr():
    """Test Item __repr__ method."""
    item = Item(id=1, item_type="Mouse", sub_type="Wireless", quantity=10)
    repr_str = repr(item)
    
    assert "Item" in repr_str
    assert "id=1" in repr_str
    assert "Mouse" in repr_str

def test_transaction_creation():
    """Test creating a Transaction instance."""
    trans = Transaction(
        item_id=1,
        transaction_type=TransactionType.ADD,
        quantity_change=5,
        quantity_before=0,
        quantity_after=5,
        notes="Initial stock"
    )
    
    assert trans.item_id == 1
    assert trans.transaction_type == TransactionType.ADD
    assert trans.quantity_change == 5
    assert trans.quantity_before == 0
    assert trans.quantity_after == 5

def test_transaction_types():
    """Test TransactionType enum."""
    assert TransactionType.ADD.value == "add"
    assert TransactionType.REMOVE.value == "remove"
```

5. Create `tests/test_repositories.py`:
```python
"""Tests for repository layer."""
import pytest
from repositories import ItemRepository, TransactionRepository
from models import TransactionType

def test_create_item(db_session):
    """Test creating an item through repository."""
    item = ItemRepository.create(
        item_type="Laptop",
        quantity=5,
        sub_type="Dell",
        serial_number="SN123",
        notes="Test laptop"
    )
    
    assert item.id is not None
    assert item.item_type == "Laptop"
    assert item.quantity == 5

def test_get_item_by_id(db_session, sample_item):
    """Test retrieving an item by ID."""
    item = ItemRepository.get_by_id(sample_item.id)
    
    assert item is not None
    assert item.id == sample_item.id
    assert item.item_type == sample_item.item_type

def test_get_nonexistent_item(db_session):
    """Test retrieving a non-existent item."""
    item = ItemRepository.get_by_id(99999)
    assert item is None

def test_get_all_items(db_session, sample_items):
    """Test retrieving all items."""
    items = ItemRepository.get_all()
    assert len(items) >= 3

def test_update_item(db_session, sample_item):
    """Test updating an item."""
    updated = ItemRepository.update(
        item_id=sample_item.id,
        item_type="Updated Laptop",
        notes="Updated notes"
    )
    
    assert updated is not None
    assert updated.item_type == "Updated Laptop"
    assert updated.notes == "Updated notes"

def test_delete_item(db_session, sample_item):
    """Test deleting an item."""
    result = ItemRepository.delete(sample_item.id)
    assert result is True
    
    # Verify it's gone
    item = ItemRepository.get_by_id(sample_item.id)
    assert item is None

def test_add_quantity(db_session, sample_item):
    """Test adding quantity to an item."""
    original_qty = sample_item.quantity
    updated = ItemRepository.add_quantity(sample_item.id, 3, "Added stock")
    
    assert updated.quantity == original_qty + 3

def test_remove_quantity(db_session, sample_item):
    """Test removing quantity from an item."""
    original_qty = sample_item.quantity
    updated = ItemRepository.remove_quantity(sample_item.id, 2, "Removed stock")
    
    assert updated.quantity == original_qty - 2

def test_remove_too_much_quantity(db_session, sample_item):
    """Test removing more quantity than available raises error."""
    with pytest.raises(ValueError):
        ItemRepository.remove_quantity(sample_item.id, 999, "Too much")

def test_search_items(db_session, sample_items):
    """Test searching items."""
    results = ItemRepository.search("Laptop")
    assert len(results) >= 1
    assert any(item.item_type == "Laptop" for item in results)

def test_search_by_field(db_session, sample_items):
    """Test searching items by specific field."""
    results = ItemRepository.search("Logitech", field="sub_type")
    assert len(results) >= 1
    assert all("Logitech" in (item.sub_type or "") for item in results)

def test_find_by_fields(db_session, sample_item):
    """Test finding item by exact field match."""
    found = ItemRepository.find_by_fields(
        item_type=sample_item.item_type,
        sub_type=sample_item.sub_type,
        serial_number=sample_item.serial_number,
        notes=sample_item.notes
    )
    
    assert found is not None
    assert found.id == sample_item.id
```

6. Create `tests/test_services.py`:
```python
"""Tests for service layer."""
import pytest
from services import InventoryService, SearchService
from repositories import ItemRepository

def test_create_item(db_session):
    """Test creating item through service."""
    item = InventoryService.create_item(
        item_type="Monitor",
        quantity=2,
        sub_type="LG",
        notes="Test monitor"
    )
    
    assert item.id is not None
    assert item.item_type == "Monitor"
    assert item.quantity == 2

def test_create_or_merge_new_item(db_session):
    """Test creating new item when no match exists."""
    item, was_merged = InventoryService.create_or_merge_item(
        item_type="Keyboard",
        quantity=5,
        sub_type="Mechanical"
    )
    
    assert item.id is not None
    assert was_merged is False
    assert item.quantity == 5

def test_create_or_merge_existing_item(db_session):
    """Test merging with existing item."""
    # Create first item
    first = InventoryService.create_item(
        item_type="Mouse",
        quantity=3,
        sub_type="Wireless",
        serial_number="",
        notes=""
    )
    
    # Try to create same item - should merge
    second, was_merged = InventoryService.create_or_merge_item(
        item_type="Mouse",
        quantity=2,
        sub_type="Wireless",
        serial_number="",
        notes=""
    )
    
    assert was_merged is True
    assert second.id == first.id
    assert second.quantity == first.quantity + 2

def test_get_all_items(db_session, sample_items):
    """Test getting all items through service."""
    items = InventoryService.get_all_items()
    assert len(items) >= 3

def test_update_item(db_session, sample_item):
    """Test updating item through service."""
    updated = InventoryService.update_item(
        item_id=sample_item.id,
        notes="Updated via service"
    )
    
    assert updated.notes == "Updated via service"

def test_delete_item(db_session, sample_item):
    """Test deleting item through service."""
    result = InventoryService.delete_item(sample_item.id)
    assert result is True

def test_add_quantity(db_session, sample_item):
    """Test adding quantity through service."""
    original = sample_item.quantity
    updated = InventoryService.add_quantity(sample_item.id, 5, "Stock added")
    
    assert updated.quantity == original + 5

def test_remove_quantity(db_session, sample_item):
    """Test removing quantity through service."""
    original = sample_item.quantity
    updated = InventoryService.remove_quantity(sample_item.id, 1, "Item sold")
    
    assert updated.quantity == original - 1

def test_search(db_session, sample_items):
    """Test search through service."""
    results = SearchService.search("Laptop", save_to_history=False)
    assert len(results) >= 1
```

7. Create `pytest.ini` in project root:
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    -v
    --strict-markers
    --tb=short
    --cov=.
    --cov-report=html
    --cov-report=term-missing
```

**Running tests:**
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov

# Run specific test file
pytest tests/test_repositories.py

# Run specific test
pytest tests/test_repositories.py::test_create_item

# Run with verbose output
pytest -v
```

**Testing:**
- Run `pytest` and verify all tests pass
- Check coverage report in `htmlcov/index.html`
- Aim for >80% code coverage

---

## Phase 3: Features & UX (Day 3)

### Step 6: Add Export/Import Functionality (Priority: MEDIUM)

**Objective:** Allow users to export inventory data to CSV/Excel and import from CSV.

**Files to create:**
- `import_export.py`

**Files to modify:**
- `ui_entities/main_window.py`
- `ui/MainWindow.ui` (add Export/Import buttons)

**Instructions:**

1. Install dependencies:
```bash
pip install openpyxl
```

2. Update `requirements.txt`:
```txt
PyQt6>=6.0.0
SQLAlchemy>=2.0.0
alembic>=1.13.0
openpyxl>=3.1.0
```

3. Create `import_export.py`:
```python
"""Import/Export functionality for inventory data."""
import csv
from datetime import datetime
from typing import List, Tuple
from pathlib import Path
import openpyxl
from openpyxl.styles import Font, PatternFill
from logger import logger
from repositories import ItemRepository
from services import InventoryService
from models import Item

class ExportService:
    """Service for exporting inventory data."""
    
    @staticmethod
    def export_to_csv(filepath: str) -> Tuple[bool, str]:
        """Export all inventory items to CSV file.
        
        Args:
            filepath: Path to CSV file
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            items = ItemRepository.get_all()
            
            with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                
                # Header
                writer.writerow([
                    'ID', 'Type', 'Sub-Type', 'Quantity', 
                    'Serial Number', 'Notes', 'Created At', 'Updated At'
                ])
                
                # Data
                for item in items:
                    writer.writerow([
                        item.id,
                        item.item_type,
                        item.sub_type or '',
                        item.quantity,
                        item.serial_number or '',
                        item.notes or '',
                        item.created_at.strftime('%Y-%m-%d %H:%M:%S') if item.created_at else '',
                        item.updated_at.strftime('%Y-%m-%d %H:%M:%S') if item.updated_at else ''
                    ])
            
            logger.info(f"Exported {len(items)} items to CSV: {filepath}")
            return (True, f"Successfully exported {len(items)} items")
            
        except Exception as e:
            logger.error(f"Failed to export to CSV: {e}", exc_info=True)
            return (False, f"Export failed: {str(e)}")
    
    @staticmethod
    def export_to_excel(filepath: str) -> Tuple[bool, str]:
        """Export all inventory items to Excel file.
        
        Args:
            filepath: Path to Excel file (.xlsx)
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            items = ItemRepository.get_all()
            
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Inventory"
            
            # Header row with styling
            headers = ['ID', 'Type', 'Sub-Type', 'Quantity', 
                      'Serial Number', 'Notes', 'Created At', 'Updated At']
            
            header_font = Font(bold=True, color="FFFFFF")
            header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
            
            for col, header in enumerate(headers, start=1):
                cell = ws.cell(row=1, column=col, value=header)
                cell.font = header_font
                cell.fill = header_fill
            
            # Data rows
            for row, item in enumerate(items, start=2):
                ws.cell(row=row, column=1, value=item.id)
                ws.cell(row=row, column=2, value=item.item_type)
                ws.cell(row=row, column=3, value=item.sub_type or '')
                ws.cell(row=row, column=4, value=item.quantity)
                ws.cell(row=row, column=5, value=item.serial_number or '')
                ws.cell(row=row, column=6, value=item.notes or '')
                ws.cell(row=row, column=7, value=item.created_at.strftime('%Y-%m-%d %H:%M:%S') if item.created_at else '')
                ws.cell(row=row, column=8, value=item.updated_at.strftime('%Y-%m-%d %H:%M:%S') if item.updated_at else '')
            
            # Auto-adjust column widths
            for column in ws.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                ws.column_dimensions[column_letter].width = adjusted_width
            
            wb.save(filepath)
            logger.info(f"Exported {len(items)} items to Excel: {filepath}")
            return (True, f"Successfully exported {len(items)} items")
            
        except Exception as e:
            logger.error(f"Failed to export to Excel: {e}", exc_info=True)
            return (False, f"Export failed: {str(e)}")


class ImportService:
    """Service for importing inventory data."""
    
    @staticmethod
    def import_from_csv(filepath: str, merge_duplicates: bool = True) -> Tuple[bool, str, int, int]:
        """Import inventory items from CSV file.
        
        Args:
            filepath: Path to CSV file
            merge_duplicates: If True, merge with existing items; if False, create new
            
        Returns:
            Tuple of (success: bool, message: str, items_created: int, items_merged: int)
        """
        try:
            created_count = 0
            merged_count = 0
            errors = []
            
            with open(filepath, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                
                for row_num, row in enumerate(reader, start=2):
                    try:
                        item_type = row.get('Type', '').strip()
                        quantity_str = row.get('Quantity', '0').strip()
                        
                        if not item_type:
                            errors.append(f"Row {row_num}: Type is required")
                            continue
                        
                        try:
                            quantity = int(quantity_str)
                            if quantity < 0:
                                errors.append(f"Row {row_num}: Quantity must be positive")
                                continue
                        except ValueError:
                            errors.append(f"Row {row_num}: Invalid quantity '{quantity_str}'")
                            continue
                        
                        # Import item
                        if merge_duplicates:
                            item, was_merged = InventoryService.create_or_merge_item(
                                item_type=item_type,
                                quantity=quantity,
                                sub_type=row.get('Sub-Type', '').strip(),
                                serial_number=row.get('Serial Number', '').strip(),
                                notes=row.get('Notes', '').strip()
                            )
                            if was_merged:
                                merged_count += 1
                            else:
                                created_count += 1
                        else:
                            InventoryService.create_item(
                                item_type=item_type,
                                quantity=quantity,
                                sub_type=row.get('Sub-Type', '').strip(),
                                serial_number=row.get('Serial Number', '').strip(),
                                notes=row.get('Notes', '').strip()
                            )
                            created_count += 1
                            
                    except Exception as e:
                        errors.append(f"Row {row_num}: {str(e)}")
            
            # Build result message
            message_parts = []
            if created_count > 0:
                message_parts.append(f"{created_count} items created")
            if merged_count > 0:
                message_parts.append(f"{merged_count} items merged")
            if errors:
                message_parts.append(f"{len(errors)} errors")
            
            message = ", ".join(message_parts)
            
            if errors:
                error_log = "\n".join(errors[:10])  # Show first 10 errors
                if len(errors) > 10:
                    error_log += f"\n... and {len(errors) - 10} more errors"
                message += f"\n\nErrors:\n{error_log}"
                logger.warning(f"Import completed with errors: {message}")
            else:
                logger.info(f"Import successful: {message}")
            
            return (True, message, created_count, merged_count)
            
        except Exception as e:
            logger.error(f"Failed to import from CSV: {e}", exc_info=True)
            return (False, f"Import failed: {str(e)}", 0, 0)
```

4. Add menu actions to `ui_entities/main_window.py`:
```python
from PyQt6.QtWidgets import QFileDialog, QMessageBox
from import_export import ExportService, ImportService

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # ... existing init code
        
        # Connect export/import actions
        self._connect_import_export_actions()
    
    def _connect_import_export_actions(self):
        """Connect import/export menu actions."""
        # Assuming you have menu actions in the UI file
        if hasattr(self, 'actionExportCSV'):
            self.actionExportCSV.triggered.connect(self._on_export_csv)
        if hasattr(self, 'actionExportExcel'):
            self.actionExportExcel.triggered.connect(self._on_export_excel)
        if hasattr(self, 'actionImportCSV'):
            self.actionImportCSV.triggered.connect(self._on_import_csv)
    
    def _on_export_csv(self):
        """Handle export to CSV."""
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Export to CSV",
            f"inventory_export_{datetime.now().strftime('%Y%m%d')}.csv",
            "CSV Files (*.csv)"
        )
        
        if filepath:
            success, message = ExportService.export_to_csv(filepath)
            if success:
                QMessageBox.information(self, "Export Successful", message)
            else:
                QMessageBox.critical(self, "Export Failed", message)
    
    def _on_export_excel(self):
        """Handle export to Excel."""
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Export to Excel",
            f"inventory_export_{datetime.now().strftime('%Y%m%d')}.xlsx",
            "Excel Files (*.xlsx)"
        )
        
        if filepath:
            success, message = ExportService.export_to_excel(filepath)
            if success:
                QMessageBox.information(self, "Export Successful", message)
            else:
                QMessageBox.critical(self, "Export Failed", message)
    
    def _on_import_csv(self):
        """Handle import from CSV."""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Import from CSV",
            "",
            "CSV Files (*.csv)"
        )
        
        if filepath:
            # Ask user if they want to merge duplicates
            reply = QMessageBox.question(
                self,
                "Import Options",
                "Merge with existing items if fields match?\n\n"
                "Yes: Add quantities to existing items\n"
                "No: Create all as new items",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            
            merge = (reply == QMessageBox.StandardButton.Yes)
            
            success, message, created, merged = ImportService.import_from_csv(filepath, merge)
            
            if success:
                QMessageBox.information(self, "Import Complete", message)
                # Refresh the list
                self._refresh_item_list()
            else:
                QMessageBox.critical(self, "Import Failed", message)
```

5. Add menu items to `ui/MainWindow.ui`:
- Open in Qt Designer
- Add a "File" menu if not exists
- Add actions: "Export to CSV", "Export to Excel", "Import from CSV"
- Or you can add them programmatically in `main_window.py`

**Testing:**
- Export inventory to CSV - open in Excel/spreadsheet
- Export to Excel - verify formatting
- Import CSV with valid data - verify items created
- Import CSV with duplicate items - verify merging
- Import CSV with invalid data - verify error handling

---

### Step 7: Add Keyboard Shortcuts (Priority: MEDIUM)

**Objective:** Add keyboard shortcuts for common operations.

**Files to modify:**
- `ui_entities/main_window.py`

**Instructions:**

1. Add keyboard shortcuts to `main_window.py`:
```python
from PyQt6.QtGui import QKeySequence, QShortcut, QAction

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # ... existing init
        
        self._setup_shortcuts()
    
    def _setup_shortcuts(self):
        """Set up keyboard shortcuts."""
        # Ctrl+N - New Item
        self.shortcut_new = QShortcut(QKeySequence.StandardKey.New, self)
        self.shortcut_new.activated.connect(self._on_add_clicked)
        
        # Ctrl+F - Focus Search
        self.shortcut_search = QShortcut(QKeySequence.StandardKey.Find, self)
        self.shortcut_search.activated.connect(self._focus_search)
        
        # Ctrl+R - Refresh List
        self.shortcut_refresh = QShortcut(QKeySequence.StandardKey.Refresh, self)
        self.shortcut_refresh.activated.connect(self._refresh_item_list)
        
        # Ctrl+E - Export
        self.shortcut_export = QShortcut(QKeySequence("Ctrl+E"), self)
        self.shortcut_export.activated.connect(self._on_export_csv)
        
        # Ctrl+I - Import
        self.shortcut_import = QShortcut(QKeySequence("Ctrl+I"), self)
        self.shortcut_import.activated.connect(self._on_import_csv)
        
        # Delete - Delete selected item
        self.shortcut_delete = QShortcut(QKeySequence.StandardKey.Delete, self)
        self.shortcut_delete.activated.connect(self._delete_selected_item)
        
        # Escape - Clear search
        self.shortcut_escape = QShortcut(QKeySequence("Escape"), self)
        self.shortcut_escape.activated.connect(self._on_search_cleared)
        
        # F5 - Refresh
        self.shortcut_f5 = QShortcut(QKeySequence("F5"), self)
        self.shortcut_f5.activated.connect(self._refresh_item_list)
        
        logger.info("Keyboard shortcuts configured")
    
    def _focus_search(self):
        """Focus the search field."""
        if hasattr(self, 'search_widget'):
            self.search_widget.setFocus()
            logger.debug("Search field focused via shortcut")
    
    def _delete_selected_item(self):
        """Delete the currently selected item."""
        current_index = self.inventory_list.currentIndex()
        if current_index.isValid():
            row = current_index.row()
            item = self.inventory_model.get_item(row)
            if item:
                self._on_delete_item(row, item)
```

2. Add status bar to show shortcuts:
```python
def _setup_ui(self):
    """Set up UI with localized strings."""
    self.setWindowTitle(tr("app.title"))
    
    # Add status bar with shortcuts hint
    self.statusBar().showMessage(
        "Shortcuts: Ctrl+N (New) | Ctrl+F (Search) | Ctrl+E (Export) | "
        "Ctrl+I (Import) | F5 (Refresh) | Del (Delete)"
    )
```

**Testing:**
- Press Ctrl+N - should open add item dialog
- Press Ctrl+F - should focus search field
- Select an item, press Delete - should prompt to delete
- Press F5 - should refresh list
- Press Escape - should clear search

---

## Phase 4: Polish & Documentation (Day 4)

### Step 8: Improve Documentation (Priority: MEDIUM)

**Objective:** Create comprehensive documentation for users and developers.

**Files to create:**
- `docs/USER_GUIDE.md`
- `docs/DEVELOPER_GUIDE.md`
- `docs/API.md`
- `CHANGELOG.md`

**Files to modify:**
- `README.md`

**Instructions:**

1. Update `README.md`:
```markdown
# AuditMagic

<div align="center">
  
![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-green.svg)
![PyQt6](https://img.shields.io/badge/PyQt6-6.0+-orange.svg)
![License](https://img.shields.io/badge/license-MIT-purple.svg)

**A modern, feature-rich inventory management application built with PyQt6**

[Features](#features) •
[Installation](#installation) •
[Usage](#usage) •
[Documentation](#documentation) •
[Development](#development)

</div>

---

## ✨ Features

### Core Functionality
- ✅ **Inventory Management** - Add, edit, delete, and track inventory items
- ✅ **Quantity Tracking** - Add/remove quantities with full transaction history
- ✅ **Advanced Search** - Search across all fields with autocomplete
- ✅ **Transaction History** - View complete audit trail for each item
- ✅ **Export/Import** - Export to CSV/Excel, import from CSV

### User Experience
- 🌍 **Multilingual** - Ukrainian and English support
- ⌨️ **Keyboard Shortcuts** - Efficient keyboard navigation
- 🎨 **Clean Interface** - Modern, intuitive PyQt6 UI
- 💾 **Auto-save** - All changes saved automatically to SQLite database

### Technical Features
- 🔒 **Data Integrity** - SQLAlchemy ORM with migrations
- 📊 **Transaction Logging** - Complete audit trail
- 🧪 **Well Tested** - Comprehensive test suite with pytest
- 📝 **Detailed Logging** - Application and error logging
- ⚙️ **Configurable** - User preferences and settings

---

## 📦 Installation

### Requirements
- Python 3.11 or higher
- Windows / macOS / Linux

### Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/AuditMagic.git
   cd AuditMagic
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   
   # Windows
   .venv\Scripts\activate
   
   # macOS/Linux
   source .venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**
   ```bash
   python main.py
   ```

---

## 🚀 Usage

### Basic Operations

#### Adding Items
1. Click **Add Item** button or press `Ctrl+N`
2. Fill in item details (Type is required)
3. Click **Save**

#### Searching
1. Click search field or press `Ctrl+F`
2. Type to search across all fields
3. Use autocomplete suggestions
4. Press `Escape` to clear search

#### Managing Quantities
1. Right-click on an item
2. Select **Add Quantity** or **Remove Quantity**
3. Enter amount and optional notes

#### Viewing History
1. Right-click on an item
2. Select **View Transactions**
3. See complete audit trail

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+N` | New item |
| `Ctrl+F` | Focus search |
| `Ctrl+E` | Export to CSV |
| `Ctrl+I` | Import from CSV |
| `Ctrl+R` / `F5` | Refresh list |
| `Delete` | Delete selected item |
| `Escape` | Clear search |

### Export/Import

**Export:**
- File → Export to CSV/Excel
- Choose location and format
- All current inventory exported

**Import:**
- File → Import from CSV
- Choose merge or create new
- Validation performed automatically

---

## 📚 Documentation

- [User Guide](docs/USER_GUIDE.md) - Detailed usage instructions
- [Developer Guide](docs/DEVELOPER_GUIDE.md) - Contributing and development
- [API Documentation](docs/API.md) - Code reference
- [Changelog](CHANGELOG.md) - Version history

---

## 🛠️ Development

### Setup Development Environment

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest

# Run with coverage
pytest --cov

# Format code
black .

# Type checking
mypy .
```

### Project Structure

```
AuditMagic/
├── main.py                 # Application entry point
├── config.py              # Configuration management
├── logger.py              # Logging setup
├── db.py                  # Database layer
├── models.py              # SQLAlchemy models
├── repositories.py        # Data access layer
├── services.py            # Business logic layer
├── validators.py          # Input validation
├── import_export.py       # Export/import functionality
├── ui/                    # Qt Designer UI files
├── ui_entities/           # UI components
│   ├── main_window.py
│   ├── inventory_model.py
│   ├── translations.py
│   └── ...
├── tests/                 # Test suite
├── alembic/              # Database migrations
└── docs/                 # Documentation
```

### Architecture

**Layered Architecture:**
```
UI Layer (PyQt6 Widgets)
    ↓
Service Layer (Business Logic)
    ↓
Repository Layer (Data Access)
    ↓
Database Layer (SQLAlchemy ORM)
    ↓
SQLite Database
```

**Design Patterns:**
- Repository Pattern for data access
- Service Layer for business logic
- MVC with QAbstractListModel
- Dependency Injection via parameters

---

## 🧪 Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_repositories.py

# Run with verbose output
pytest -v

# Generate coverage report
pytest --cov --cov-report=html
open htmlcov/index.html
```

Current test coverage: **>80%**

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Please ensure:
- Code is formatted with Black
- Tests pass (`pytest`)
- Type hints are used
- Documentation is updated

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- PyQt6 for the UI framework
- SQLAlchemy for ORM
- Alembic for migrations
- All contributors and users

---

## 📧 Contact

For questions, issues, or suggestions:
- GitHub Issues: [Create an issue](https://github.com/yourusername/AuditMagic/issues)
- Email: your.email@example.com

---

<div align="center">
Made with ❤️ by [Your Name]
</div>
```

2. Create `CHANGELOG.md`:
```markdown
# Changelog

All notable changes to AuditMagic will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-02-09

### Added
- Initial release
- Core inventory management features
- Transaction history tracking
- Search with autocomplete
- Export to CSV/Excel
- Import from CSV
- Multilingual support (Ukrainian, English)
- Keyboard shortcuts
- Database migrations with Alembic
- Comprehensive logging system
- Configuration management
- Input validation
- Test suite with >80% coverage

### Features
- Add, edit, delete inventory items
- Track quantities with full audit trail
- Advanced search across all fields
- Export/import data
- User preferences and settings
- Keyboard navigation
- Transaction history viewer

### Technical
- PyQt6 UI framework
- SQLAlchemy ORM
- SQLite database
- Alembic migrations
- Pytest test suite
- Black code formatting
- Type hints throughout

## [Unreleased]

### Planned Features
- Barcode/QR code scanning
- Analytics dashboard
- Dark mode
- Multi-user support
- Cloud backup
- Mobile app
```

**Testing:**
- Review all documentation for accuracy
- Verify all links work
- Ensure code examples are correct
- Check screenshots if added

---

## Summary Checklist

After completing all steps, verify:

### Phase 1 - Foundation
- [ ] Logging system working
- [ ] Configuration saves/loads
- [ ] Database migrations setup
- [ ] Logs directory created

### Phase 2 - Quality
- [ ] Input validators working
- [ ] All tests passing
- [ ] >80% code coverage
- [ ] No validation bypass bugs

### Phase 3 - Features
- [ ] Export CSV works
- [ ] Export Excel works
- [ ] Import CSV works
- [ ] Keyboard shortcuts work
- [ ] Duplicate merging works

### Phase 4 - Polish
- [ ] README updated
- [ ] CHANGELOG created
- [ ] User guide written
- [ ] Code documented

---

## Next Steps (Future Enhancements)

After completing the above, consider:

1. **Barcode Support** - Add barcode/QR scanning
2. **Analytics** - Dashboard with charts and reports
3. **Dark Mode** - Theme switching
4. **Backup** - Automated database backups
5. **PDF Export** - Export inventory reports to PDF
6. **User Preferences Dialog** - GUI for settings
7. **Notifications** - Low stock alerts
8. **Categories** - Hierarchical item categorization
9. **Multi-language** - Add more language translations
10. **Cloud Sync** - Optional cloud backup/sync

---

## Troubleshooting

**If tests fail:**
- Ensure virtual environment is activated
- Check all dependencies installed
- Verify Python version >= 3.11
- Check database permissions

**If logging doesn't work:**
- Verify `~/.audit_magic/logs/` directory exists
- Check file permissions
- Review logger.py configuration

**If imports fail after adding:**
- Clear the database and re-import
- Check CSV encoding (should be UTF-8)
- Verify CSV headers match expected format

---

## Support

For implementation help:
- Review error logs in `~/.audit_magic/logs/`
- Check pytest output for test failures
- Review this guide step-by-step
- Ask questions in GitHub issues

Good luck with the implementation! 🚀
