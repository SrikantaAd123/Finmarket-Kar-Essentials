
"""
Finmarket Kart Essentials
Dedicated SQLAlchemy metadata for commerce tables.

This declarative base is separate from the legacy
WorkSphere database metadata.
"""

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase


# =========================================================
# NAMING CONVENTION
# =========================================================

COMMERCE_CONSTRAINTS = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": (
        "fk_%(table_name)s_%(column_0_name)s_"
        "%(referred_table_name)s"
    ),
    "pk": "pk_%(table_name)s",
}


# =========================================================
# COMMERCE DECLARATIVE BASE
# =========================================================

class CommerceBase(DeclarativeBase):
    """
    Base class for every Finmarket Kart Essentials
    commerce SQLAlchemy model.

    All commerce models share this metadata registry.
    """

    metadata = MetaData(
        naming_convention=COMMERCE_CONSTRAINTS,
    )


__all__ = [
    "COMMERCE_CONSTRAINTS",
    "CommerceBase",
]
