
"""
Product catalogue models for Finmarket Kart Essentials.

Contains:
- Category
- Brand
- Product
- ProductImage
- ProductVariant
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.commerce_base import CommerceBase

from backend.models.mixins import (
    PrimaryKeyMixin,
    TimestampMixin,
    SoftDeleteMixin,
    ActiveStatusMixin,
)


# =========================================================
# CATEGORY MODEL
# =========================================================

class Category(
    CommerceBase,
    PrimaryKeyMixin,
    TimestampMixin,
    SoftDeleteMixin,
    ActiveStatusMixin,
):
    """Product category with optional parent category."""

    __tablename__ = "categories"

    __table_args__ = (
        UniqueConstraint(
            "slug",
            name="uq_categories_slug",
        ),
        Index(
            "ix_categories_parent_id",
            "parent_id",
        ),
    )

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    slug: Mapped[str] = mapped_column(
        String(180),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    image_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "categories.id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    display_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    # -----------------------------------------------------
    # SELF-REFERENTIAL RELATIONSHIPS
    # -----------------------------------------------------

    parent: Mapped[Category | None] = relationship(
        "Category",
        remote_side="Category.id",
        back_populates="children",
    )

    children: Mapped[list[Category]] = relationship(
        "Category",
        back_populates="parent",
    )

    # -----------------------------------------------------
    # PRODUCT RELATIONSHIP
    # -----------------------------------------------------

    products: Mapped[list[Product]] = relationship(
        "Product",
        back_populates="category",
    )

    def __repr__(self) -> str:
        return (
            f"<Category "
            f"id={self.id} "
            f"name={self.name!r}>"
        )


# =========================================================
# BRAND MODEL
# =========================================================

class Brand(
    CommerceBase,
    PrimaryKeyMixin,
    TimestampMixin,
    SoftDeleteMixin,
    ActiveStatusMixin,
):
    """Product brand information."""

    __tablename__ = "brands"

    __table_args__ = (
        UniqueConstraint(
            "slug",
            name="uq_brands_slug",
        ),
    )

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    slug: Mapped[str] = mapped_column(
        String(180),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    logo_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    products: Mapped[list[Product]] = relationship(
        "Product",
        back_populates="brand",
    )

    def __repr__(self) -> str:
        return (
            f"<Brand "
            f"id={self.id} "
            f"name={self.name!r}>"
        )


# =========================================================
# PRODUCT MODEL
# =========================================================

class Product(
    CommerceBase,
    PrimaryKeyMixin,
    TimestampMixin,
    SoftDeleteMixin,
    ActiveStatusMixin,
):
    """Main product catalogue record."""

    __tablename__ = "products"

    __table_args__ = (
        UniqueConstraint(
            "sku",
            name="uq_products_sku",
        ),
        UniqueConstraint(
            "slug",
            name="uq_products_slug",
        ),
        CheckConstraint(
            "price >= 0",
            name="price_nonnegative",
        ),
        CheckConstraint(
            "compare_at_price IS NULL "
            "OR compare_at_price >= 0",
            name="compare_price_nonnegative",
        ),
        Index(
            "ix_products_category_id",
            "category_id",
        ),
        Index(
            "ix_products_brand_id",
            "brand_id",
        ),
        Index(
            "ix_products_is_published",
            "is_published",
        ),
    )

    # -----------------------------------------------------
    # PRODUCT INFORMATION
    # -----------------------------------------------------

    sku: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    slug: Mapped[str] = mapped_column(
        String(280),
        nullable=False,
    )

    short_description: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Legacy storefront columns already present in the products table.
    # Keeping these mapped allows the public API and existing SQL seed
    # scripts to expose product photos and stock without a schema migration.
    image_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    stock_quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    # -----------------------------------------------------
    # CATEGORY AND BRAND FOREIGN KEYS
    # -----------------------------------------------------

    category_id: Mapped[int] = mapped_column(
        ForeignKey(
            "categories.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    brand_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "brands.id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    # -----------------------------------------------------
    # PRICING INFORMATION
    # -----------------------------------------------------

    price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    compare_at_price: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="INR",
        server_default="INR",
    )

    # -----------------------------------------------------
    # PRODUCT MEASUREMENT
    # -----------------------------------------------------

    unit: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="piece",
        server_default="piece",
    )

    weight_value: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 3),
        nullable=True,
    )

    weight_unit: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    # -----------------------------------------------------
    # PRODUCT VISIBILITY
    # -----------------------------------------------------

    is_published: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
    )

    is_featured: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
    )

    # -----------------------------------------------------
    # CATEGORY RELATIONSHIP
    # -----------------------------------------------------

    category: Mapped[Category] = relationship(
        "Category",
        back_populates="products",
    )

    # -----------------------------------------------------
    # BRAND RELATIONSHIP
    # -----------------------------------------------------

    brand: Mapped[Brand | None] = relationship(
        "Brand",
        back_populates="products",
    )

    # -----------------------------------------------------
    # IMAGE RELATIONSHIP
    # -----------------------------------------------------

    images: Mapped[list[ProductImage]] = relationship(
        "ProductImage",
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="ProductImage.display_order",
    )

    # -----------------------------------------------------
    # VARIANT RELATIONSHIP
    # -----------------------------------------------------

    variants: Mapped[list[ProductVariant]] = relationship(
        "ProductVariant",
        back_populates="product",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<Product "
            f"id={self.id} "
            f"sku={self.sku!r} "
            f"name={self.name!r}>"
        )


# =========================================================
# PRODUCT IMAGE MODEL
# =========================================================

class ProductImage(
    CommerceBase,
    PrimaryKeyMixin,
    TimestampMixin,
):
    """Images associated with a product."""

    __tablename__ = "product_images"

    __table_args__ = (
        Index(
            "ix_product_images_product_id",
            "product_id",
        ),
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey(
            "products.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    image_url: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
    )

    alt_text: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
    )

    display_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    product: Mapped[Product] = relationship(
        "Product",
        back_populates="images",
    )


# =========================================================
# PRODUCT VARIANT MODEL
# =========================================================

class ProductVariant(
    CommerceBase,
    PrimaryKeyMixin,
    TimestampMixin,
    SoftDeleteMixin,
    ActiveStatusMixin,
):
    """Different purchasable versions of a product."""

    __tablename__ = "product_variants"

    __table_args__ = (
        UniqueConstraint(
            "sku",
            name="uq_product_variants_sku",
        ),
        CheckConstraint(
            "price >= 0",
            name="price_nonnegative",
        ),
        Index(
            "ix_product_variants_product_id",
            "product_id",
        ),
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey(
            "products.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    sku: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(180),
        nullable=False,
    )

    price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    attributes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    product: Mapped[Product] = relationship(
        "Product",
        back_populates="variants",
    )


# =========================================================
# PUBLIC EXPORTS
# =========================================================

__all__ = [
    "Category",
    "Brand",
    "Product",
    "ProductImage",
    "ProductVariant",
]
