
"""Initialize database tables for Finmarket Kart Essentials."""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from backend.database.connection import engine, Base
from backend.database.commerce_base import CommerceBase

# Import model modules so SQLAlchemy registers their tables.
import backend.models.user
import backend.models.project
import backend.models.task
import backend.models.activity
import backend.models.audit
import backend.models.auth_session

import backend.models.customer
import backend.models.catalog
import backend.models.cart
import backend.models.order
import backend.models.order_tracking
import backend.models.payment
import backend.models.payment_webhook
import backend.models.delivery
import backend.models.inventory
import backend.models.notification
import backend.models.commerce

logger = logging.getLogger(__name__)


def initialize_database() -> None:
    """Create all registered WorkSphere and Commerce tables."""

    try:
        with engine.begin() as connection:
            connection.execute(text("SELECT 1"))

            # Legacy WorkSphere tables.
            Base.metadata.create_all(bind=connection)

            # Finmarket commerce tables.
            CommerceBase.metadata.create_all(bind=connection)

        logger.info("Database tables initialized successfully.")

    except SQLAlchemyError:
        logger.exception("Database initialization failed.")
        raise


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    initialize_database()
