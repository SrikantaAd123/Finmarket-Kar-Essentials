
"""
Reusable SQLAlchemy mixins for Finmarket Kart Essentials.

Provides:
- PrimaryKeyMixin
- TimestampMixin
- SoftDeleteMixin
- ActiveStatusMixin
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Integer,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column


# =========================================================
# UTC DATETIME HELPER
# =========================================================

def utc_now() -> datetime:
    """Return the current timezone-aware UTC datetime."""

    return datetime.now(timezone.utc)


# =========================================================
# PRIMARY KEY MIXIN
# =========================================================

class PrimaryKeyMixin:
    """Provides an auto-incrementing integer primary key."""

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )


# =========================================================
# TIMESTAMP MIXIN
# =========================================================

class TimestampMixin:
    """Provides creation and update timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


# =========================================================
# SOFT DELETE MIXIN
# =========================================================

class SoftDeleteMixin:
    """
    Supports soft deletion.

    Records are marked deleted instead of being
    permanently removed from the database.
    """

    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
        index=True,
    )

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


# =========================================================
# ACTIVE STATUS MIXIN
# =========================================================

class ActiveStatusMixin:
    """Provides an active/inactive status."""

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
        index=True,
    )


# =========================================================
# PUBLIC EXPORTS
# =========================================================

__all__ = [
    "utc_now",
    "PrimaryKeyMixin",
    "TimestampMixin",
    "SoftDeleteMixin",
    "ActiveStatusMixin",
]
