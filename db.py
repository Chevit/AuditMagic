"""Database layer with SQLAlchemy session management."""
import os
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from models import Base

# Database file path - stored in user's app data directory
APP_DATA_DIR = os.path.join(os.path.expanduser("~"), ".audit_magic")
DATABASE_PATH = os.path.join(APP_DATA_DIR, "inventory.db")
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# Create engine with SQLite
engine = None
SessionLocal = None


def init_database(db_url: str = None) -> None:
    """Initialize the database engine and create all tables.

    Args:
        db_url: Optional database URL. If not provided, uses default SQLite path.
                Use "sqlite:///:memory:" for in-memory database.
    """
    global engine, SessionLocal

    if db_url is None:
        db_url = DATABASE_URL
        # Ensure app data directory exists
        os.makedirs(APP_DATA_DIR, exist_ok=True)
    elif db_url == ":memory:":
        db_url = "sqlite:///:memory:"

    engine = create_engine(
        db_url,
        echo=False,  # Set to True for SQL debugging
        connect_args={"check_same_thread": False}  # Required for SQLite
    )

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Create all tables
    Base.metadata.create_all(bind=engine)


def get_engine():
    """Get the database engine, initializing if necessary."""
    if engine is None:
        init_database()
    return engine


def get_session() -> Session:
    """Get a new database session.

    Returns:
        A new SQLAlchemy Session instance.
    """
    if SessionLocal is None:
        init_database()
    return SessionLocal()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Provide a transactional scope around a series of operations.

    Usage:
        with session_scope() as session:
            session.add(item)
            # Changes are automatically committed on success
            # or rolled back on exception

    Yields:
        A SQLAlchemy Session instance.
    """
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def reset_database() -> None:
    """Drop all tables and recreate them. USE WITH CAUTION!"""
    if engine is not None:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
