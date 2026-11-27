
"""
Finmarket Kart Essentials - Customer Models.

Contains:
- Customer
- CustomerAddress
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    func,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from backend.database.commerce_base import CommerceBase


if TYPE_CHECKING:
    from backend.models.cart import Cart
    from backend.models.order import Order


# =========================================================
# CUSTOMER MODEL
# =========================================================

class Customer(CommerceBase):
    """Stores customer identity and profile information."""

    __tablename__ = "customers"

    __table_args__ = (
        Index("ix_customers_email", "email"),
        Index("ix_customers_active", "is_active"),
    )

    # -----------------------------------------------------
    # PRIMARY KEY
    # -----------------------------------------------------

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    # -----------------------------------------------------
    # ZITADEL IDENTITY
    # -----------------------------------------------------

    zitadel_sub: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
    )

    # -----------------------------------------------------
    # CUSTOMER PROFILE
    # -----------------------------------------------------

    full_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    phone_number: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    profile_image_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    # -----------------------------------------------------
    # CUSTOMER STATUS
    # -----------------------------------------------------

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    email_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    phone_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # -----------------------------------------------------
    # TIMESTAMPS
    # -----------------------------------------------------

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

    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # -----------------------------------------------------
    # CART RELATIONSHIP
    # -----------------------------------------------------

    carts: Mapped[list[Cart]] = relationship(
        "Cart",
        back_populates="customer",
        cascade="all, delete-orphan",
    )

    # -----------------------------------------------------
    # ORDER RELATIONSHIP
    # -----------------------------------------------------

    orders: Mapped[list[Order]] = relationship(
        "Order",
        back_populates="customer",
    )

    # -----------------------------------------------------
    # ADDRESS RELATIONSHIP
    # -----------------------------------------------------

    addresses: Mapped[list[CustomerAddress]] = relationship(
        "CustomerAddress",
        back_populates="customer",
        cascade="all, delete-orphan",
    )

    # -----------------------------------------------------
    # OBJECT REPRESENTATION
    # -----------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"<Customer("
            f"id={self.id}, "
            f"email={self.email!r}"
            f")>"
        )


# =========================================================
# CUSTOMER ADDRESS MODEL
# =========================================================

class CustomerAddress(CommerceBase):
    """Stores customer delivery and billing addresses."""

    __tablename__ = "customer_addresses"

    # -----------------------------------------------------
    # PRIMARY KEY
    # -----------------------------------------------------

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    # -----------------------------------------------------
    # CUSTOMER FOREIGN KEY
    # -----------------------------------------------------

    customer_id: Mapped[int] = mapped_column(
        ForeignKey(
            "customers.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    # -----------------------------------------------------
    # ADDRESS INFORMATION
    # -----------------------------------------------------

    address_type: Mapped[str] = mapped_column(
        String(30),
        default="home",
        nullable=False,
    )

    recipient_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    phone_number: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    address_line_1: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    address_line_2: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    landmark: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    city: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    state: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    country: Mapped[str] = mapped_column(
        String(100),
        default="India",
        nullable=False,
    )

    postal_code: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    # -----------------------------------------------------
    # ADDRESS SETTINGS
    # -----------------------------------------------------

    is_default: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # -----------------------------------------------------
    # TIMESTAMPS
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # CUSTOMER RELATIONSHIP
    # -----------------------------------------------------

    customer: Mapped[Customer] = relationship(
        "Customer",
        back_populates="addresses",
    )

    # -----------------------------------------------------
    # OBJECT REPRESENTATION
    # -----------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"<CustomerAddress("
            f"id={self.id}, "
            f"customer_id={self.customer_id}, "
            f"postal_code={self.postal_code!r}"
            f")>"
        )


__all__ = [
    "Customer",
    "CustomerAddress",
]
