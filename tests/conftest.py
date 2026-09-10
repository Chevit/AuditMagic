import os
import sys

import pytest

os.environ.setdefault("AUDITMAGIC_DB", ":memory:")
# Defensive default: CI sets this explicitly, but nothing here should hang
# headless just because a local run forgot to.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


@pytest.fixture(autouse=True)
def fresh_db():
    """Reinitialise an in-memory DB before every test."""
    from core.db import init_database

    init_database(":memory:")
