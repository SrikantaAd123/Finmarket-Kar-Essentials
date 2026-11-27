
"""Product catalogue Pydantic schemas for Finmarket Kart Essentials."""

from __future__ import annotations

from decimal import Decimal

from pydantic import Field, field_validator, model_validator

from backend.schemas.common import BaseSchema, TimestampSchema


# =========================================================
# CATEGORY SCHEMAS
# =========================================================

class CategoryBase(BaseSchema):
    """Shared category fields."""

    name: str = Field(
        min_length=2,
        max_length=150,
    )

    slug: str = Field(
        min_length=2,
        max_length=180,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    )

    description: str | None = Field(
        default=None,
        max_length=5000,
    )

    image_url: str | None = Field(
        default=None,
        max_length=500,
    )

    parent_id: int | None = Field(
        default=None,
        gt=0,
    )

    display_order: int = Field(
        default=0,
        ge=0,
    )


class CategoryCreate(CategoryBase):
    """Request schema for creating a category."""


class CategoryUpdate(BaseSchema):
    """Request schema for partially updating a category."""

    name: str | None = Field(
        default=None,
        min_length=2,
        max_length=150,
    )

    slug: str | None = Field(
        default=None,
        min_length=2,
        max_length=180,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    )

    description: str | None = Field(
        default=None,
        max_length=5000,
    )

    image_url: str | None = Field(
        default=None,
        max_length=500,
    )

    parent_id: int | None = Field(
        default=None,
        gt=0,
    )

    display_order: int | None = Field(
        default=None,
        ge=0,
    )

    is_active: bool | None = None


class CategoryResponse(CategoryBase, TimestampSchema):
    """Category information returned by the API."""

    id: int = Field(gt=0)

    is_active: bool


# =========================================================
# BRAND SCHEMAS
# =========================================================

class BrandBase(BaseSchema):
    """Shared brand fields."""

    name: str = Field(
        min_length=2,
        max_length=150,
    )

    slug: str = Field(
        min_length=2,
        max_length=180,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    )

    description: str | None = Field(
        default=None,
        max_length=5000,
    )

    logo_url: str | None = Field(
        default=None,
        max_length=500,
    )


class BrandCreate(BrandBase):
    """Request schema for creating a brand."""


class BrandUpdate(BaseSchema):
    """Request schema for updating a brand."""

    name: str | None = Field(
        default=None,
        min_length=2,
        max_length=150,
    )

    slug: str | None = Field(
        default=None,
        min_length=2,
        max_length=180,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    )

    description: str | None = Field(
        default=None,
        max_length=5000,
    )

    logo_url: str | None = Field(
        default=None,
        max_length=500,
    )

    is_active: bool | None = None


class BrandResponse(BrandBase, TimestampSchema):
    """Brand information returned by the API."""

    id: int = Field(gt=0)

    is_active: bool


# =========================================================
# PRODUCT IMAGE SCHEMAS
# =========================================================

class ProductImageCreate(BaseSchema):
    """Request schema for adding a product image."""

    image_url: str = Field(
        min_length=1,
        max_length=1000,
    )

    alt_text: str | None = Field(
        default=None,
        max_length=255,
    )

    is_primary: bool = False

    display_order: int = Field(
        default=0,
        ge=0,
    )


class ProductImageResponse(ProductImageCreate, TimestampSchema):
    """Product image response."""

    id: int = Field(gt=0)


# =========================================================
# PRODUCT VARIANT SCHEMAS
# =========================================================

class ProductVariantCreate(BaseSchema):
    """Request schema for creating a product variant."""

    sku: str = Field(
        min_length=2,
        max_length=80,
    )

    name: str = Field(
        min_length=2,
        max_length=180,
    )

    price: Decimal = Field(
        ge=Decimal("0.00"),
        max_digits=12,
        decimal_places=2,
    )

    attributes: str | None = Field(
        default=None,
        max_length=2000,
    )


class ProductVariantResponse(
    ProductVariantCreate,
    TimestampSchema,
):
    """Product variant response."""

    id: int = Field(gt=0)

    product_id: int = Field(gt=0)

    is_active: bool


# =========================================================
# PRODUCT SCHEMAS
# =========================================================

class ProductBase(BaseSchema):
    """Common product information."""

    sku: str = Field(
        min_length=2,
        max_length=80,
    )

    name: str = Field(
        min_length=2,
        max_length=255,
    )

    slug: str = Field(
        min_length=2,
        max_length=280,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    )

    short_description: str | None = Field(
        default=None,
        max_length=500,
    )

    description: str | None = Field(
        default=None,
        max_length=10000,
    )

    category_id: int = Field(gt=0)

    brand_id: int | None = Field(
        default=None,
        gt=0,
    )

    price: Decimal = Field(
        gt=Decimal("0.00"),
        max_digits=12,
        decimal_places=2,
    )

    compare_at_price: Decimal | None = Field(
        default=None,
        ge=Decimal("0.00"),
        max_digits=12,
        decimal_places=2,
    )

    currency: str = Field(
        default="INR",
        min_length=3,
        max_length=3,
    )

    unit: str = Field(
        default="piece",
        min_length=1,
        max_length=50,
    )

    weight_value: Decimal | None = Field(
        default=None,
        gt=Decimal("0"),
        max_digits=10,
        decimal_places=3,
    )

    weight_unit: str | None = Field(
        default=None,
        max_length=20,
    )

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        """Normalize currency to uppercase."""
        return value.upper()

    @model_validator(mode="after")
    def validate_comparison_price(self) -> ProductBase:
        """Comparison price must not be lower than selling price."""

        if (
            self.compare_at_price is not None
            and self.compare_at_price < self.price
        ):
            raise ValueError(
                "Compare-at price must be greater than "
                "or equal to the selling price."
            )

        return self


class ProductCreate(ProductBase):
    """Request schema for creating a product."""

    images: list[ProductImageCreate] = Field(
        default_factory=list,
        max_length=20,
    )

    variants: list[ProductVariantCreate] = Field(
        default_factory=list,
        max_length=50,
    )

    # New admin products should appear in the public catalogue by default.
    # CatalogService enforces that a published product has at least one image.
    is_published: bool = True

    is_featured: bool = False


class ProductUpdate(BaseSchema):
    """Request schema for partially updating a product."""

    sku: str | None = Field(
        default=None,
        min_length=2,
        max_length=80,
    )

    name: str | None = Field(
        default=None,
        min_length=2,
        max_length=255,
    )

    slug: str | None = Field(
        default=None,
        min_length=2,
        max_length=280,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    )

    short_description: str | None = Field(
        default=None,
        max_length=500,
    )

    description: str | None = Field(
        default=None,
        max_length=10000,
    )

    category_id: int | None = Field(
        default=None,
        gt=0,
    )

    brand_id: int | None = Field(
        default=None,
        gt=0,
    )

    price: Decimal | None = Field(
        default=None,
        gt=Decimal("0.00"),
        max_digits=12,
        decimal_places=2,
    )

    compare_at_price: Decimal | None = Field(
        default=None,
        ge=Decimal("0.00"),
        max_digits=12,
        decimal_places=2,
    )

    currency: str | None = Field(
        default=None,
        min_length=3,
        max_length=3,
    )

    unit: str | None = Field(
        default=None,
        min_length=1,
        max_length=50,
    )

    weight_value: Decimal | None = Field(
        default=None,
        gt=Decimal("0"),
        max_digits=10,
        decimal_places=3,
    )

    weight_unit: str | None = Field(
        default=None,
        max_length=20,
    )

    is_active: bool | None = None

    is_published: bool | None = None

    is_featured: bool | None = None

    @field_validator("currency")
    @classmethod
    def validate_currency(
        cls,
        value: str | None,
    ) -> str | None:
        """Normalize an optional currency value."""
        if value is not None:
            return value.upper()

        return value

    @model_validator(mode="after")
    def validate_comparison_price(self) -> ProductUpdate:
        """Validate comparison price when both prices are supplied."""

        if (
            self.price is not None
            and self.compare_at_price is not None
            and self.compare_at_price < self.price
        ):
            raise ValueError(
                "Compare-at price must be greater than "
                "or equal to the selling price."
            )

        return self


class ProductResponse(
    ProductBase,
    TimestampSchema,
):
    """Detailed product response."""

    id: int = Field(gt=0)

    is_active: bool

    is_published: bool

    is_featured: bool

    images: list[ProductImageResponse] = Field(
        default_factory=list,
    )

    variants: list[ProductVariantResponse] = Field(
        default_factory=list,
    )


# =========================================================
# PRODUCT LISTING AND FILTER SCHEMAS
# =========================================================

class ProductFilter(BaseSchema):
    """Filters for product listing and search."""

    search: str | None = Field(
        default=None,
        max_length=150,
    )

    category_id: int | None = Field(
        default=None,
        gt=0,
    )

    brand_id: int | None = Field(
        default=None,
        gt=0,
    )

    minimum_price: Decimal | None = Field(
        default=None,
        ge=Decimal("0.00"),
    )

    maximum_price: Decimal | None = Field(
        default=None,
        ge=Decimal("0.00"),
    )

    is_featured: bool | None = None

    sort_by: str = Field(
        default="created_at",
        pattern=r"^(created_at|name|price)$",
    )

    sort_order: str = Field(
        default="desc",
        pattern=r"^(asc|desc)$",
    )

    @model_validator(mode="after")
    def validate_price_range(self) -> ProductFilter:
        """Ensure minimum price does not exceed maximum price."""

        if (
            self.minimum_price is not None
            and self.maximum_price is not None
            and self.minimum_price > self.maximum_price
        ):
            raise ValueError(
                "Minimum price cannot exceed maximum price."
            )

        return self


__all__ = [
    "CategoryBase",
    "CategoryCreate",
    "CategoryUpdate",
    "CategoryResponse",
    "BrandBase",
    "BrandCreate",
    "BrandUpdate",
    "BrandResponse",
    "ProductImageCreate",
    "ProductImageResponse",
    "ProductVariantCreate",
    "ProductVariantResponse",
    "ProductBase",
    "ProductCreate",
    "ProductUpdate",
    "ProductResponse",
    "ProductFilter",
]
