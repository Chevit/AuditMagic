"""The two schema sources must agree.

Tests build their schema with ``Base.metadata.create_all``; users get theirs
from Alembic. If the two drift, a constraint can hold in production while the
suite happily accepts rows that violate it. This test compares them
semantically (nullability, defaults, types, uniqueness) rather than by DDL
text, since batch-mode migrations legitimately reorder columns and rename
constraints.
"""

import os
import sqlite3
import sys

import pytest
from sqlalchemy import create_engine

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _build_alembic_schema(path: str) -> None:
    """Run every migration into *path*.

    ``alembic/env.py`` reads ``core.db.DATABASE_URL`` at import time and offers
    no override, so patch it before the upgrade — otherwise this would migrate
    the developer's real database.
    """
    import core.db

    original = core.db.DATABASE_URL
    core.db.DATABASE_URL = f"sqlite:///{path}"
    try:
        from alembic import command
        from alembic.config import Config

        cfg = Config(os.path.join(PROJECT_ROOT, "alembic.ini"))
        cfg.set_main_option("script_location", os.path.join(PROJECT_ROOT, "alembic"))
        command.upgrade(cfg, "head")
    finally:
        core.db.DATABASE_URL = original


def _build_create_all_schema(path: str) -> None:
    from core.models import Base

    Base.metadata.create_all(create_engine(f"sqlite:///{path}"))


def _introspect(path: str) -> dict:
    conn = sqlite3.connect(path)
    try:
        schema = {}
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'alembic%' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
        for (table,) in tables:
            columns = {
                name: {
                    "type": ctype,
                    "notnull": bool(notnull),
                    "default": default,
                    "pk": bool(pk),
                }
                for _, name, ctype, notnull, default, pk in conn.execute(
                    f"PRAGMA table_info('{table}')"
                )
            }
            unique_on = set()
            for _, index_name, is_unique, _, _ in conn.execute(
                f"PRAGMA index_list('{table}')"
            ):
                if is_unique:
                    cols = tuple(
                        row[2]
                        for row in conn.execute(f"PRAGMA index_info('{index_name}')")
                    )
                    unique_on.add(cols)
            schema[table] = {"columns": columns, "unique_on": unique_on}
        return schema
    finally:
        conn.close()


@pytest.fixture(scope="module")
def schemas(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("schema")
    create_all_db = str(tmp / "create_all.db")
    alembic_db = str(tmp / "alembic.db")
    # Build create_all first: importing alembic's env mutates core.db state.
    _build_create_all_schema(create_all_db)
    _build_alembic_schema(alembic_db)
    return _introspect(alembic_db), _introspect(create_all_db)


def test_same_tables(schemas):
    alembic_schema, create_all_schema = schemas
    assert set(alembic_schema) == set(create_all_schema)


def test_same_columns(schemas):
    alembic_schema, create_all_schema = schemas
    for table in sorted(alembic_schema):
        assert set(alembic_schema[table]["columns"]) == set(
            create_all_schema[table]["columns"]
        ), f"column set differs for {table}"


@pytest.mark.parametrize("attribute", ["notnull", "default", "type", "pk"])
def test_column_definitions_match(schemas, attribute):
    alembic_schema, create_all_schema = schemas
    mismatches = []
    for table in sorted(alembic_schema):
        for column, spec in sorted(alembic_schema[table]["columns"].items()):
            other = create_all_schema[table]["columns"].get(column)
            if other is None:
                continue
            if (spec[attribute] or None) != (other[attribute] or None):
                mismatches.append(
                    f"{table}.{column}: alembic={spec[attribute]!r} "
                    f"create_all={other[attribute]!r}"
                )
    assert not mismatches, f"{attribute} differs:\n" + "\n".join(mismatches)


def test_same_uniqueness(schemas):
    alembic_schema, create_all_schema = schemas
    for table in sorted(alembic_schema):
        assert (
            alembic_schema[table]["unique_on"] == create_all_schema[table]["unique_on"]
        ), f"uniqueness differs for {table}"
