
"""WorkSphere user database model."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.connection import Base


if TYPE_CHECKING:
    from backend.models.project import Project
    from backend.models.task import Task
    from backend.models.activity import Activity


class User(Base):
    """Stores WorkSphere employee and administrator information."""

    __tablename__ = "users"

    # ========================================================
    # PRIMARY KEY
    # ========================================================

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    # ========================================================
    # ZITADEL IDENTITY
    # ========================================================

    zitadel_sub: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )

    full_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )

    # ========================================================
    # EMPLOYEE INFORMATION
    # ========================================================

    department: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    job_title: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    # ========================================================
    # ACCOUNT STATUS
    # ========================================================

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # ========================================================
    # TIMESTAMPS
    # ========================================================

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # ========================================================
    # PROJECT RELATIONSHIP
    # ========================================================

    projects: Mapped[list["Project"]] = relationship(
        back_populates="owner",
        foreign_keys="Project.owner_id",
    )

    # ========================================================
    # TASK RELATIONSHIP
    # ========================================================

    assigned_tasks: Mapped[list["Task"]] = relationship(
        back_populates="assignee",
        foreign_keys="Task.assignee_id",
    )

    # ========================================================
    # ACTIVITY RELATIONSHIP
    # ========================================================

    activities: Mapped[list["Activity"]] = relationship(
        back_populates="actor",
    )

    # ========================================================
    # OBJECT REPRESENTATION
    # ========================================================

    def __repr__(self) -> str:
        return (
            f"<User("
            f"id={self.id}, "
            f"email={self.email}"
            f")>"
        )
