import os
import sys
import pytest

os.environ.setdefault("AUDITMAGIC_DB", ":memory:")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


@pytest.fixture(autouse=True)
def fresh_db():
    """Reinitialise an in-memory DB before every test."""
    from core.db import init_database
    init_database(":memory:")
