
"""
Database package for Finmarket Kart Essentials.

Exports the dedicated commerce declarative base.

Import database sessions and engine directly from:
    backend.database.connection
"""

from backend.database.commerce_base import (
    COMMERCE_CONSTRAINTS,
    CommerceBase,
)


__all__ = [
    "COMMERCE_CONSTRAINTS",
    "CommerceBase",
]
