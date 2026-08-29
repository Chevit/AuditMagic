"""Database layer with SQLAlchemy session management."""

import os
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Generator, Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from core.logger import APP_DATA_DIR, logger
from core.models import Base

# Database file path - stored in user's app data directory
DATABASE_PATH = os.path.join(APP_DATA_DIR, "inventory.db")
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# Create engine with SQLite; both are populated by init_database()
engine: Optional[Engine] = None
SessionLocal: Optional[sessionmaker] = None

# The session of the innermost open unit_of_work, if any. Repository calls made
# inside one join its transaction instead of opening their own.
_active_session: ContextVar[Optional[Session]] = ContextVar(
    "auditmagic_active_session", default=None
)


def init_database(db_url: Optional[str] = None) -> None:
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
        logger.info(f"Database directory created/verified: {APP_DATA_DIR}")
    elif db_url == ":memory:":
        db_url = "sqlite:///:memory:"
        logger.info("Using in-memory database")

    logger.info(f"Initializing database with URL: {db_url}")

    engine = create_engine(
        db_url,
        echo=False,  # Set to True for SQL debugging
        connect_args={"check_same_thread": False},  # Required for SQLite
    )

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Create all tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized successfully")


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
    assert SessionLocal is not None
    session: Session = SessionLocal()
    return session


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Provide a transactional scope around a series of operations.

    Inside an open unit_of_work this joins that transaction and commits
    nothing: the outermost scope owns the commit, so a composed write either
    lands whole or not at all.

    Usage:
        with session_scope() as session:
            session.add(item)
            # Changes are automatically committed on success
            # or rolled back on exception

    Yields:
        A SQLAlchemy Session instance.
    """
    active = _active_session.get()
    if active is not None:
        yield active
        return

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


@contextmanager
def unit_of_work() -> Generator[Session, None, None]:
    """Run several repository calls inside one transaction.

    Repository methods each open their own session_scope, so a service that
    composes two of them used to produce two transactions — and a failure
    between them left the first one committed. Wrapping the service in a unit
    of work makes the whole operation atomic; nested units join the outer one.

    Usage:
        with unit_of_work():
            item_type = ItemTypeRepository.get_or_create(...)
            ItemRepository.create(item_type_id=item_type.id, ...)

    Yields:
        The session every nested repository call will use.
    """
    active = _active_session.get()
    if active is not None:
        yield active
        return

    session = get_session()
    token = _active_session.set(session)
    try:
        yield session
        session.commit()
        logger.debug("Unit of work committed successfully")
    except Exception as e:
        session.rollback()
        logger.error(f"Unit of work failed, rolled back: {str(e)}", exc_info=True)
        raise
    finally:
        _active_session.reset(token)
        session.close()


def run_migrations() -> None:
    """Run database migrations using Alembic."""
    from alembic import command
    from alembic.config import Config
    from runtime import resource_path

    logger.info("Running database migrations...")

    alembic_cfg = Config(resource_path("alembic.ini"))
    alembic_cfg.set_main_option("script_location", resource_path("alembic"))

    try:
        command.upgrade(alembic_cfg, "head")
        logger.info("Database migrations completed successfully")
    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        raise


def reset_database() -> None:
    """Drop all tables and recreate them. USE WITH CAUTION!"""
    if engine is not None:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
