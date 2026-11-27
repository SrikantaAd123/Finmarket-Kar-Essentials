"""Audit log model for Finmarket Kart Essentials."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    DateTime,
    Index,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.commerce_base import CommerceBase
from backend.models.mixins import PrimaryKeyMixin


class AuditLog(
    CommerceBase,
    PrimaryKeyMixin,
):
    """Stores important business and administrative audit events.

    Records actions performed by customers, administrators,
    employees, or automated system processes.
    """

    __tablename__ = "audit_logs"

    __table_args__ = (
        Index(
            "ix_audit_logs_actor",
            "actor_type",
            "actor_id",
        ),
        Index(
            "ix_audit_logs_entity",
            "entity_type",
            "entity_id",
        ),
        Index(
            "ix_audit_logs_action",
            "action",
        ),
        Index(
            "ix_audit_logs_created_at",
            "created_at",
        ),
    )

    # ========================================================
    # ACTOR INFORMATION
    # ========================================================

    actor_type: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default="system",
        server_default="system",
    )

    actor_id: Mapped[int | None] = mapped_column(
        nullable=True,
    )

    actor_name: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    # ========================================================
    # ACTION INFORMATION
    # ========================================================

    action: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # ========================================================
    # AFFECTED ENTITY INFORMATION
    # ========================================================

    entity_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    entity_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    # ========================================================
    # CHANGE DETAILS
    # ========================================================

    old_values: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    new_values: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    extra_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    # ========================================================
    # REQUEST INFORMATION
    # ========================================================

    ip_address: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
    )

    user_agent: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    request_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    # ========================================================
    # TIMESTAMP
    # ========================================================

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # ========================================================
    # OBJECT REPRESENTATION
    # ========================================================

    def __repr__(self) -> str:
        return (
            f"<AuditLog("
            f"id={self.id}, "
            f"action={self.action!r}, "
            f"entity_type={self.entity_type!r}, "
            f"entity_id={self.entity_id!r}"
            f")>"
        )


