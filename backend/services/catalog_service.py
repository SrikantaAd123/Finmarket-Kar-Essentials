
"""Catalogue service for Finmarket Kart Essentials.

Contains business logic for:
- Categories
- Brands
- Products
- Product images
- Product variants

The service validates requests and delegates database operations
to CatalogRepository. Transaction commits are managed by the caller.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from backend.repositories.catalog_repository import CatalogRepository


class CatalogService:
    """Business logic layer for the product catalogue."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = CatalogRepository(db)

    # =========================================================
    # COMMON HELPERS
    # =========================================================

    @staticmethod
    def _model_data(
        data: Any,
        *,
        exclude_unset: bool = True,
    ) -> dict[str, Any]:
        """Convert a Pydantic model or dictionary into a dictionary."""

        if isinstance(data, dict):
            return data.copy()

        if hasattr(data, "model_dump"):
            return data.model_dump(exclude_unset=exclude_unset)

        raise TypeError(
            "Input must be a dictionary or a Pydantic model."
        )

    @staticmethod
    def _validate_id(value: int, field_name: str = "ID") -> None:
        if value <= 0:
            raise ValueError(f"{field_name} must be greater than zero.")

    @staticmethod
    def _validate_pagination(
        page: int,
        page_size: int,
    ) -> None:
        if page < 1:
            raise ValueError("Page must be at least 1.")

        if not 1 <= page_size <= 100:
            raise ValueError(
                "Page size must be between 1 and 100."
            )

    @staticmethod
    def _validate_price_range(
        minimum_price: Decimal | None,
        maximum_price: Decimal | None,
    ) -> None:
        if minimum_price is not None and minimum_price < 0:
            raise ValueError("Minimum price cannot be negative.")

        if maximum_price is not None and maximum_price < 0:
            raise ValueError("Maximum price cannot be negative.")

        if (
            minimum_price is not None
            and maximum_price is not None
            and minimum_price > maximum_price
        ):
            raise ValueError(
                "Minimum price cannot exceed maximum price."
            )

    # =========================================================
    # CATEGORY OPERATIONS
    # =========================================================

    def create_category(self, data: Any):
        """Create a new product category."""

        category_data = self._model_data(data)

        if not category_data.get("name"):
            raise ValueError("Category name is required.")

        if not category_data.get("slug"):
            raise ValueError("Category slug is required.")

        return self.repository.create_category(category_data)

    def get_category(self, category_id: int):
        """Get a category by its ID."""

        self._validate_id(category_id, "Category ID")

        category = self.repository.get_category_by_id(category_id)

        if category is None:
            raise ValueError("Category not found.")

        return category

    def get_category_by_slug(self, slug: str):
        """Get a category by its URL slug."""

        if not slug or not slug.strip():
            raise ValueError("Category slug is required.")

        category = self.repository.get_category_by_slug(
            slug.strip()
        )

        if category is None:
            raise ValueError("Category not found.")

        return category

    def get_all_categories(self):
        """Return all categories."""

        return self.repository.get_all_categories()

    def get_root_categories(self):
        """Return categories that do not have a parent."""

        return self.repository.get_root_categories()

    def get_category_children(self, category_id: int):
        """Return immediate child categories."""

        self._validate_id(category_id, "Category ID")

        self.get_category(category_id)

        return self.repository.get_category_children(category_id)

    def update_category(
        self,
        category_id: int,
        data: Any,
    ):
        """Update an existing category."""

        self._validate_id(category_id, "Category ID")

        category_data = self._model_data(data)

        if not category_data:
            raise ValueError("No category fields were provided.")

        category = self.repository.update_category(
            category_id,
            category_data,
        )

        if category is None:
            raise ValueError("Category not found.")

        return category

    # =========================================================
    # BRAND OPERATIONS
    # =========================================================

    def create_brand(self, data: Any):
        """Create a new brand."""

        brand_data = self._model_data(data)

        if not brand_data.get("name"):
            raise ValueError("Brand name is required.")

        if not brand_data.get("slug"):
            raise ValueError("Brand slug is required.")

        return self.repository.create_brand(brand_data)

    def get_brand(self, brand_id: int):
        """Get a brand by its ID."""

        self._validate_id(brand_id, "Brand ID")

        brand = self.repository.get_brand_by_id(brand_id)

        if brand is None:
            raise ValueError("Brand not found.")

        return brand

    def get_brand_by_slug(self, slug: str):
        """Get a brand by its URL slug."""

        if not slug or not slug.strip():
            raise ValueError("Brand slug is required.")

        brand = self.repository.get_brand_by_slug(slug.strip())

        if brand is None:
            raise ValueError("Brand not found.")

        return brand

    def get_all_brands(self):
        """Return all brands."""

        return self.repository.get_all_brands()

    def update_brand(
        self,
        brand_id: int,
        data: Any,
    ):
        """Update an existing brand."""

        self._validate_id(brand_id, "Brand ID")

        brand_data = self._model_data(data)

        if not brand_data:
            raise ValueError("No brand fields were provided.")

        brand = self.repository.update_brand(
            brand_id,
            brand_data,
        )

        if brand is None:
            raise ValueError("Brand not found.")

        return brand

    # =========================================================
    # PRODUCT OPERATIONS
    # =========================================================

    
    def create_product(self, data: Any):
        """Create a product with images and variants."""

        product_data = self._model_data(data)

        required_fields = (
            "sku",
            "name",
            "slug",
            "category_id",
            "price",
        )

        for field in required_fields:
            if product_data.get(field) is None:
                raise ValueError(
                    f"Product field '{field}' is required."
                )

        category_id = int(product_data["category_id"])
        self._validate_id(category_id, "Category ID")

        category = self.repository.get_category_by_id(category_id)

        if category is None or getattr(category, "is_deleted", False):
            raise ValueError(
                f"Category ID {category_id} does not exist."
            )

        if not getattr(category, "is_active", True):
            raise ValueError(
                f"Category ID {category_id} is inactive."
            )

        if product_data.get("brand_id") is not None:
            self._validate_id(
                int(product_data["brand_id"]),
                "Brand ID",
            )

        price = Decimal(str(product_data["price"]))

        if price < 0:
            raise ValueError("Product price cannot be negative.")

        compare_at_price = product_data.get("compare_at_price")

        if compare_at_price is not None:
            compare_at_price = Decimal(str(compare_at_price))

            if compare_at_price < price:
                raise ValueError(
                    "Compare-at price cannot be lower than product price."
                )

        # Normalize nested Pydantic models and dictionaries.
        images = product_data.get("images") or []
        variants = product_data.get("variants") or []

        normalized_images = [
            self._model_data(image)
            for image in images
        ]

        normalized_variants = [
            self._model_data(variant)
            for variant in variants
        ]

        # Require actual image URLs before publishing.
        for image in normalized_images:
            image_url = str(image.get("image_url") or "").strip()

            if not image_url or image_url == "string":
                raise ValueError(
                    "Every product image must have a valid image_url."
                )

            image["image_url"] = image_url

        if product_data.get("is_published") and not normalized_images:
            raise ValueError(
                "Add at least one valid product image before publishing."
            )

        product_data["images"] = normalized_images
        product_data["variants"] = normalized_variants

        # Repository inserts the product, images and variants.
        return self.repository.create_product(product_data)

    def get_product(self, product_id: int):
        """Get a product by ID."""

        self._validate_id(product_id, "Product ID")

        product = self.repository.get_product_by_id(product_id)

        if product is None:
            raise ValueError("Product not found.")

        return product

    def get_product_details(self, product_id: int):
        """Get a product together with its images and variants."""

        self._validate_id(product_id, "Product ID")

        product = self.repository.get_product_details(product_id)

        if product is None:
            raise ValueError("Product not found.")

        return product

    def get_product_by_slug(self, slug: str):
        """Get a product by its URL slug."""

        if not slug or not slug.strip():
            raise ValueError("Product slug is required.")

        product = self.repository.get_product_by_slug(slug.strip())

        if product is None:
            raise ValueError("Product not found.")

        return product

    def get_product_by_sku(self, sku: str):
        """Get a product by its SKU."""

        if not sku or not sku.strip():
            raise ValueError("Product SKU is required.")

        product = self.repository.get_product_by_sku(sku.strip())

        if product is None:
            raise ValueError("Product not found.")

        return product

    def search_products(
        self,
        search: str | None = None,
        category_id: int | None = None,
        brand_id: int | None = None,
        min_price: Decimal | None = None,
        max_price: Decimal | None = None,
        featured: bool | None = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        published_only: bool = True,
    ) -> tuple[list, int]:
        """Search and filter catalogue products."""

        self._validate_pagination(page, page_size)

        if category_id is not None:
            self._validate_id(category_id, "Category ID")

        if brand_id is not None:
            self._validate_id(brand_id, "Brand ID")

        self._validate_price_range(min_price, max_price)

        if sort_by not in {"created_at", "name", "price"}:
            raise ValueError("Invalid product sort field.")

        if sort_order not in {"asc", "desc"}:
            raise ValueError("Sort order must be asc or desc.")

        if search is not None:
            search = search.strip() or None

        # Important: these parameter names must match
        # CatalogRepository.search_products().
        return self.repository.search_products(
            search=search,
            category_id=category_id,
            brand_id=brand_id,
            minimum_price=min_price,
            maximum_price=max_price,
            is_featured=featured,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
            published_only=published_only,
        )

    def get_featured_products(self, limit: int = 12):
        """Return featured products."""

        if not 1 <= limit <= 100:
            raise ValueError(
                "Featured product limit must be between 1 and 100."
            )

        return self.repository.get_featured_products(limit=limit)

    def get_products_by_category(
        self,
        category_id: int,
        page: int = 1,
        page_size: int = 20,
    ):
        """Return products belonging to a category."""

        self._validate_id(category_id, "Category ID")
        self._validate_pagination(page, page_size)

        self.get_category(category_id)

        return self.repository.get_products_by_category(
            category_id=category_id,
            page=page,
            page_size=page_size,
        )

    def get_products_by_brand(
        self,
        brand_id: int,
        page: int = 1,
        page_size: int = 20,
    ):
        """Return products belonging to a brand."""

        self._validate_id(brand_id, "Brand ID")
        self._validate_pagination(page, page_size)

        self.get_brand(brand_id)

        return self.repository.get_products_by_brand(
            brand_id=brand_id,
            page=page,
            page_size=page_size,
        )

    def update_product(
        self,
        product_id: int,
        data: Any,
    ):
        """Update product fields."""

        self._validate_id(product_id, "Product ID")

        product_data = self._model_data(data)

        if not product_data:
            raise ValueError("No product fields were provided.")

        if "price" in product_data:
            price = Decimal(str(product_data["price"]))

            if price < 0:
                raise ValueError("Product price cannot be negative.")

        if (
            "price" in product_data
            and "compare_at_price" in product_data
            and product_data["compare_at_price"] is not None
        ):
            if (
                Decimal(str(product_data["compare_at_price"]))
                < Decimal(str(product_data["price"]))
            ):
                raise ValueError(
                    "Compare-at price cannot be lower than product price."
                )

        product = self.repository.update_product(
            product_id,
            product_data,
        )

        if product is None:
            raise ValueError("Product not found.")

        return product

    def deactivate_product(self, product_id: int):
        """Deactivate a product without deleting its history."""

        self._validate_id(product_id, "Product ID")

        product = self.repository.deactivate_product(product_id)

        if product is None:
            raise ValueError("Product not found.")

        return product

    # =========================================================
    # PRODUCT IMAGE OPERATIONS
    # =========================================================

    def add_product_image(
        self,
        product_id: int,
        data: Any,
    ):
        """Add an image to a product."""

        self._validate_id(product_id, "Product ID")

        self.get_product(product_id)

        image_data = self._model_data(data)

        if not image_data.get("image_url"):
            raise ValueError("Product image URL is required.")

        # Repository signature requires BOTH arguments.
        return self.repository.create_product_image(
            product_id,
            image_data,
        )

    def get_product_images(self, product_id: int):
        """Get all images belonging to a product."""

        self._validate_id(product_id, "Product ID")

        self.get_product(product_id)

        return self.repository.get_product_images(product_id)

    def delete_product_image(self, image_id: int) -> bool:
        """Delete a product image."""

        self._validate_id(image_id, "Image ID")

        deleted = self.repository.delete_product_image(image_id)

        if not deleted:
            raise ValueError("Product image not found.")

        return deleted

    # =========================================================
    # PRODUCT VARIANT OPERATIONS
    # =========================================================

    def add_product_variant(
        self,
        product_id: int,
        data: Any,
    ):
        """Add a variant to a product."""

        self._validate_id(product_id, "Product ID")

        self.get_product(product_id)

        variant_data = self._model_data(data)

        if not variant_data.get("sku"):
            raise ValueError("Variant SKU is required.")

        if not variant_data.get("name"):
            raise ValueError("Variant name is required.")

        # Repository signature requires BOTH arguments.
        return self.repository.create_product_variant(
            product_id,
            variant_data,
        )

    def get_product_variants(self, product_id: int):
        """Get all variants belonging to a product."""

        self._validate_id(product_id, "Product ID")

        self.get_product(product_id)

        return self.repository.get_product_variants(product_id)

    def get_variant(self, variant_id: int):
        """Get a variant by ID."""

        self._validate_id(variant_id, "Variant ID")

        variant = self.repository.get_variant_by_id(variant_id)

        if variant is None:
            raise ValueError("Product variant not found.")

        return variant

    # =========================================================
    # CATALOGUE STATISTICS
    # =========================================================

    def get_catalogue_statistics(self) -> dict[str, int]:
        """Return basic catalogue counts."""

        return {
            "total_products": self.repository.count_products(),
            "published_products": (
                self.repository.count_published_products()
            ),
            "total_categories": self.repository.count_categories(),
            "total_brands": self.repository.count_brands(),
        }
