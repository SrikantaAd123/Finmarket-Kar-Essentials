
"""
Finmarket Kart Essentials - MySQL Database Connection.

Provides:
- MySQL SQLAlchemy engine.
- Database session factory.
- WorkSphere declarative Base.
- Finmarket CommerceBase import.
- FastAPI database dependency.
- Database connectivity check.
- Connection pool disposal.

IMPORTANT:
WorkSphere Base and Finmarket CommerceBase use
separate SQLAlchemy metadata registries.
"""

from __future__ import annotations

import logging
import os

from collections.abc import Generator
from pathlib import Path

from dotenv import load_dotenv

from sqlalchemy import URL, create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from backend.database.commerce_base import CommerceBase


logger = logging.getLogger(__name__)


# =========================================================
# 1. PROJECT CONFIGURATION
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

ENV_FILE = PROJECT_ROOT / ".env"

load_dotenv(ENV_FILE)


# =========================================================
# 2. ENVIRONMENT HELPERS
# =========================================================

def _get_int_env(name: str, default: int) -> int:
    """Read an integer environment variable."""

    value = os.getenv(name)

    if value is None or not value.strip():
        return default

    try:
        return int(value)
    except ValueError as exc:
        raise RuntimeError(
            f"Environment variable {name} must be an integer."
        ) from exc


def _get_bool_env(name: str, default: bool = False) -> bool:
    """Read a boolean environment variable."""

    value = os.getenv(name)

    if value is None:
        return default

    return value.strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


# =========================================================
# 3. MYSQL CONFIGURATION
# =========================================================

DB_HOST = os.getenv("DB_HOST", "localhost").strip()

DB_PORT = _get_int_env("DB_PORT", 3306)

DB_NAME = os.getenv("DB_NAME", "").strip()

DB_USER = os.getenv("DB_USER", "root").strip()

DB_PASSWORD = os.getenv("DB_PASSWORD", "")

DB_ECHO = _get_bool_env("DB_ECHO", False)

DB_POOL_SIZE = _get_int_env("DB_POOL_SIZE", 10)

DB_MAX_OVERFLOW = _get_int_env("DB_MAX_OVERFLOW", 20)

DB_POOL_RECYCLE = _get_int_env("DB_POOL_RECYCLE", 3600)

DB_POOL_TIMEOUT = _get_int_env("DB_POOL_TIMEOUT", 30)


# =========================================================
# 4. CONFIGURATION VALIDATION
# =========================================================

if not DB_NAME:
    raise RuntimeError(
        "DB_NAME is missing. "
        "Configure DB_NAME in the project .env file."
    )

if not DB_HOST:
    raise RuntimeError("DB_HOST cannot be empty.")

if not DB_USER:
    raise RuntimeError("DB_USER cannot be empty.")

if not 1 <= DB_PORT <= 65535:
    raise RuntimeError(
        "DB_PORT must be between 1 and 65535."
    )

if DB_POOL_SIZE < 1:
    raise RuntimeError(
        "DB_POOL_SIZE must be at least 1."
    )

if DB_MAX_OVERFLOW < 0:
    raise RuntimeError(
        "DB_MAX_OVERFLOW cannot be negative."
    )

if DB_POOL_RECYCLE < 1 or DB_POOL_TIMEOUT < 1:
    raise RuntimeError(
        "Database pool recycle and timeout must be positive."
    )


# =========================================================
# 5. DATABASE URL
# =========================================================

DATABASE_URL = URL.create(
    drivername="mysql+pymysql",
    username=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=DB_PORT,
    database=DB_NAME,
    query={
        "charset": "utf8mb4",
    },
)


# =========================================================
# 6. SQLALCHEMY ENGINE
# =========================================================

engine: Engine = create_engine(
    DATABASE_URL,
    echo=DB_ECHO,
    pool_pre_ping=True,
    pool_recycle=DB_POOL_RECYCLE,
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_MAX_OVERFLOW,
    pool_timeout=DB_POOL_TIMEOUT,
)


# =========================================================
# 7. WORKSPHERE DECLARATIVE BASE
# =========================================================

class Base(DeclarativeBase):
    """
    Declarative base for legacy WorkSphere models.

    Models:
        User
        AuthSession
        Project
        Task
        Activity
    """

    pass


# =========================================================
# 8. FINMARKET COMMERCE BASE
# =========================================================

# Imported from commerce_base.py.
#
# Commerce models must inherit from CommerceBase.
# Do not replace Base with CommerceBase.
#
# This keeps both metadata registries separate.


# =========================================================
# 9. SESSION FACTORY
# =========================================================

SessionLocal = sessionmaker(
    bind=engine,
    class_=Session,
    autoflush=False,
    expire_on_commit=False,
)


# =========================================================
# 10. FASTAPI DATABASE DEPENDENCY
# =========================================================

def get_db() -> Generator[Session, None, None]:
    """
    Provide one database session per API request.

    Services manage successful commits.
    Failed requests roll back uncommitted changes.
    """

    db = SessionLocal()

    try:
        yield db

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


# =========================================================
# 11. DATABASE CONNECTION CHECK
# =========================================================

def test_database_connection() -> bool:
    """Check whether MySQL is reachable."""

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        logger.info(
            "Finmarket Kart MySQL connection successful."
        )

        return True

    except Exception as error:
        logger.error(
            "MySQL connection failed: %s",
            type(error).__name__,
        )

        return False


# =========================================================
# 12. DATABASE CONNECTION DISPOSAL
# =========================================================

def close_database_connections() -> None:
    """Dispose of pooled database connections."""

    engine.dispose()

    logger.info(
        "Database connections disposed successfully."
    )


# =========================================================
# 13. PUBLIC EXPORTS
# =========================================================

__all__ = [
    "PROJECT_ROOT",
    "ENV_FILE",
    "DATABASE_URL",
    "engine",
    "Base",
    "CommerceBase",
    "SessionLocal",
    "get_db",
    "test_database_connection",
    "close_database_connections",
]
