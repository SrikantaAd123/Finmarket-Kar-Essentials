
"""Generic SQLAlchemy repository for Finmarket Kart Essentials."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from sqlalchemy import func, inspect, select
from sqlalchemy.orm import Session
from sqlalchemy.sql import Select

from backend.database.commerce_base import CommerceBase


ModelType = TypeVar(
    "ModelType",
    bound=CommerceBase,
)


class BaseRepository(Generic[ModelType]):
    """Reusable database operations for commerce repositories."""

    def __init__(
        self,
        db: Session,
        model: type[ModelType],
    ) -> None:
        self.db = db
        self.model = model

    # =====================================================
    # INTERNAL HELPERS
    # =====================================================

    def _validate_columns(
        self,
        data: dict[str, Any],
    ) -> None:
        """Ensure supplied fields are mapped database columns."""

        mapper = inspect(self.model)

        valid_columns = {
            attribute.key
            for attribute in mapper.column_attrs
        }

        invalid_columns = set(data.keys()) - valid_columns

        if invalid_columns:
            raise ValueError(
                f"Invalid fields for {self.model.__name__}: "
                f"{', '.join(sorted(invalid_columns))}"
            )

    def _apply_filters(
        self,
        statement: Select[Any],
        filters: dict[str, Any] | None = None,
    ) -> Select[Any]:
        """Apply equality filters to a SQLAlchemy statement."""

        if not filters:
            return statement

        self._validate_columns(filters)

        for field, value in filters.items():
            column = getattr(self.model, field)

            if value is None:
                statement = statement.where(column.is_(None))
            else:
                statement = statement.where(column == value)

        return statement

    # =====================================================
    # CREATE
    # =====================================================

    def create(
        self,
        data: dict[str, Any],
    ) -> ModelType:
        """Create a new database record."""

        self._validate_columns(data)

        instance = self.model(**data)

        self.db.add(instance)
        self.db.flush()
        self.db.refresh(instance)

        return instance

    # =====================================================
    # READ
    # =====================================================

    def get_by_id(
        self,
        record_id: int,
    ) -> ModelType | None:
        """Retrieve a record using its primary key."""

        return self.db.get(
            self.model,
            record_id,
        )

    def get_all(
        self,
        offset: int = 0,
        limit: int = 20,
    ) -> list[ModelType]:
        """Retrieve records with pagination."""

        if offset < 0:
            raise ValueError("Offset cannot be negative.")

        if limit < 1:
            raise ValueError("Limit must be greater than zero.")

        statement = (
            select(self.model)
            .offset(offset)
            .limit(limit)
        )

        result = self.db.scalars(statement)

        return list(result.all())

    def get_filtered(
        self,
        filters: dict[str, Any],
        offset: int = 0,
        limit: int = 20,
    ) -> list[ModelType]:
        """Retrieve records using equality filters."""

        if offset < 0:
            raise ValueError("Offset cannot be negative.")

        if limit < 1:
            raise ValueError("Limit must be greater than zero.")

        statement = select(self.model)

        statement = self._apply_filters(
            statement,
            filters,
        )

        statement = statement.offset(offset).limit(limit)

        result = self.db.scalars(statement)

        return list(result.all())

    # =====================================================
    # UPDATE
    # =====================================================

    def update(
        self,
        instance: ModelType,
        data: dict[str, Any],
    ) -> ModelType:
        """Update an existing database record."""

        self._validate_columns(data)

        for field, value in data.items():
            setattr(instance, field, value)

        self.db.add(instance)
        self.db.flush()
        self.db.refresh(instance)

        return instance

    def update_by_id(
        self,
        record_id: int,
        data: dict[str, Any],
    ) -> ModelType | None:
        """Find and update a record by primary key."""

        instance = self.get_by_id(record_id)

        if instance is None:
            return None

        return self.update(instance, data)

    # =====================================================
    # DELETE
    # =====================================================

    def delete(
        self,
        instance: ModelType,
    ) -> bool:
        """Delete an existing database record."""

        self.db.delete(instance)
        self.db.flush()

        return True

    def delete_by_id(
        self,
        record_id: int,
    ) -> bool:
        """Find and delete a record using its primary key."""

        instance = self.get_by_id(record_id)

        if instance is None:
            return False

        return self.delete(instance)

    # =====================================================
    # COUNT
    # =====================================================

    def count(
        self,
        filters: dict[str, Any] | None = None,
    ) -> int:
        """Count database records."""

        statement = select(
            func.count()
        ).select_from(self.model)

        statement = self._apply_filters(
            statement,
            filters,
        )

        return self.db.scalar(statement) or 0

    # =====================================================
    # EXISTS
    # =====================================================

    def exists(
        self,
        filters: dict[str, Any],
    ) -> bool:
        """Check whether a matching record exists."""

        statement = (
            select(self.model)
            .where(*[
                getattr(self.model, field).is_(None)
                if value is None
                else getattr(self.model, field) == value
                for field, value in filters.items()
            ])
            .limit(1)
        )

        self._validate_columns(filters)

        return self.db.scalars(statement).first() is not None

    # =====================================================
    # GET OR CREATE
    # =====================================================

    def get_or_create(
        self,
        lookup: dict[str, Any],
        defaults: dict[str, Any] | None = None,
    ) -> tuple[ModelType, bool]:
        """Retrieve a record or create it if it does not exist.

        Returns:
            (instance, created)
        """

        instance = self.db.scalars(
            self._apply_filters(
                select(self.model),
                lookup,
            ).limit(1)
        ).first()

        if instance is not None:
            return instance, False

        create_data = {
            **lookup,
            **(defaults or {}),
        }

        instance = self.create(create_data)

        return instance, True
