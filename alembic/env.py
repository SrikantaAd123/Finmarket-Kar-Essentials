
"""Alembic environment for Finmarket Kart Essentials commerce models."""

from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context


# ============================================================
# PROJECT ROOT
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================
# DATABASE ENGINE AND COMMERCE METADATA
# ============================================================

from backend.database.connection import engine
from backend.database.commerce_base import CommerceBase


# ============================================================
# IMPORT ALL FINMARKET COMMERCE MODELS
# ============================================================

# Importing these modules registers their tables with CommerceBase.

import backend.models.audit
import backend.models.cart
import backend.models.catalog
import backend.models.commerce
import backend.models.customer
import backend.models.delivery
import backend.models.inventory
import backend.models.notification
import backend.models.order
import backend.models.order_tracking
import backend.models.payment
import backend.models.payment_webhook


# ============================================================
# ALEMBIC CONFIGURATION
# ============================================================

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


# ============================================================
# TARGET METADATA
# ============================================================

target_metadata = CommerceBase.metadata


# ============================================================
# OFFLINE MIGRATIONS
# ============================================================

def run_migrations_offline() -> None:
    """Generate SQL migration statements without connecting."""

    database_url = engine.url.render_as_string(
        hide_password=True,
    )

    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


# ============================================================
# ONLINE MIGRATIONS
# ============================================================

def run_migrations_online() -> None:
    """Run migrations using the configured database engine."""

    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


# ============================================================
# EXECUTE MIGRATIONS
# ============================================================

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
