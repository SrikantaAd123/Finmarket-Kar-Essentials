
"""Catalogue repository for Finmarket Kart Essentials.

Provides database operations for:
- Categories
- Brands
- Products
- Product images
- Product variants
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.orm import Session, selectinload

from backend.models.catalog import (
    Category,
    Brand,
    Product,
    ProductImage,
    ProductVariant,
)
from backend.repositories.base_repository import BaseRepository


class CatalogRepository:
    """Database repository for the product catalogue."""

    def __init__(self, db: Session) -> None:
        self.db = db

        self.products = BaseRepository(db, Product)
        self.categories = BaseRepository(db, Category)
        self.brands = BaseRepository(db, Brand)
        self.images = BaseRepository(db, ProductImage)
        self.variants = BaseRepository(db, ProductVariant)

    # =====================================================
    # PRODUCT OPERATIONS
    # =====================================================

    def create_product(self, data: dict) -> Product:
        """Create a product."""

        product_data = data.copy()

        # Images and variants are handled separately.
        image_data = product_data.pop("images", [])
        variant_data = product_data.pop("variants", [])

        product = self.products.create(product_data)

        for image in image_data:
            self.create_product_image(
                product.id,
                image,
            )

        for variant in variant_data:
            self.create_product_variant(
                product.id,
                variant,
            )

        self.db.flush()
        return product

    def get_product_by_id(
        self,
        product_id: int,
    ) -> Product | None:
        """Retrieve a product by ID."""

        return self.db.get(Product, product_id)

    def get_product_by_slug(
        self,
        slug: str,
    ) -> Product | None:
        """Retrieve a product using its URL slug."""

        statement = select(Product).where(
            Product.slug == slug
        )

        return self.db.scalars(statement).first()

    def get_product_by_sku(
        self,
        sku: str,
    ) -> Product | None:
        """Retrieve a product using its SKU."""

        statement = select(Product).where(
            Product.sku == sku
        )

        return self.db.scalars(statement).first()

    def get_product_details(
        self,
        product_id: int,
    ) -> Product | None:
        """Retrieve a product with images and variants."""

        statement = (
            select(Product)
            .options(
                selectinload(Product.images),
                selectinload(Product.variants),
            )
            .where(Product.id == product_id)
        )

        return self.db.scalars(statement).first()

    def search_products(
        self,
        search: str | None = None,
        category_id: int | None = None,
        brand_id: int | None = None,
        minimum_price: Decimal | None = None,
        maximum_price: Decimal | None = None,
        is_featured: bool | None = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        published_only: bool = True,
    ) -> tuple[list[Product], int]:
        """Search and filter products with pagination."""

        if page < 1:
            raise ValueError("Page must be at least 1.")

        if not 1 <= page_size <= 100:
            raise ValueError("Page size must be between 1 and 100.")

        if (
            minimum_price is not None
            and maximum_price is not None
            and minimum_price > maximum_price
        ):
            raise ValueError("Minimum price cannot exceed maximum price.")

        allowed_sort_fields = {
            "created_at": Product.created_at,
            "name": Product.name,
            "price": Product.price,
        }

        if sort_by not in allowed_sort_fields:
            raise ValueError("Unsupported product sort field.")

        if sort_order not in {"asc", "desc"}:
            raise ValueError("Sort order must be asc or desc.")

        statement = select(Product)

        conditions = []

        if published_only:
            conditions.append(Product.is_published.is_(True))
            conditions.append(Product.is_active.is_(True))
            conditions.append(Product.is_deleted.is_(False))

        if search:
            search_term = f"%{search.strip()}%"

            conditions.append(
                or_(
                    Product.name.ilike(search_term),
                    Product.sku.ilike(search_term),
                    Product.slug.ilike(search_term),
                    Product.short_description.ilike(search_term),
                )
            )

        if category_id is not None:
            conditions.append(
                Product.category_id == category_id
            )

        if brand_id is not None:
            conditions.append(
                Product.brand_id == brand_id
            )

        if minimum_price is not None:
            conditions.append(
                Product.price >= minimum_price
            )

        if maximum_price is not None:
            conditions.append(
                Product.price <= maximum_price
            )

        if is_featured is not None:
            conditions.append(
                Product.is_featured == is_featured
            )

        if conditions:
            statement = statement.where(*conditions)

        count_statement = (
            select(func.count(Product.id))
            .where(*conditions)
        )

        total = self.db.scalar(count_statement) or 0

        sort_column = allowed_sort_fields[sort_by]

        ordering = (
            asc(sort_column)
            if sort_order == "asc"
            else desc(sort_column)
        )

        statement = (
            statement
            .options(
                selectinload(Product.images),
                selectinload(Product.variants),
            )
            .order_by(ordering, Product.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        products = list(
            self.db.scalars(statement).all()
        )

        return products, total

    def get_featured_products(
        self,
        limit: int = 12,
    ) -> list[Product]:
        """Retrieve published and active featured products."""

        if not 1 <= limit <= 100:
            raise ValueError("Limit must be between 1 and 100.")

        statement = (
            select(Product)
            .options(
                selectinload(Product.images),
                selectinload(Product.variants),
            )
            .where(
                Product.is_featured.is_(True),
                Product.is_published.is_(True),
                Product.is_active.is_(True),
            )
            .order_by(Product.created_at.desc())
            .limit(limit)
        )

        return list(self.db.scalars(statement).all())

    def get_products_by_category(
        self,
        category_id: int,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Product], int]:
        """Retrieve products belonging to a category."""

        return self.search_products(
            category_id=category_id,
            page=page,
            page_size=page_size,
        )

    def get_products_by_brand(
        self,
        brand_id: int,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Product], int]:
        """Retrieve products belonging to a brand."""

        return self.search_products(
            brand_id=brand_id,
            page=page,
            page_size=page_size,
        )

    def update_product(
        self,
        product_id: int,
        data: dict,
    ) -> Product | None:
        """Update an existing product."""

        product = self.get_product_by_id(product_id)

        if product is None:
            return None

        update_data = data.copy()

        # Do not update relationships through generic field assignment.
        update_data.pop("images", None)
        update_data.pop("variants", None)

        self.products.update(
            product,
            update_data,
        )

        return product

    def deactivate_product(
        self,
        product_id: int,
    ) -> Product | None:
        """Deactivate a product without deleting its history."""

        product = self.get_product_by_id(product_id)

        if product is None:
            return None

        product.is_active = False
        product.is_published = False

        self.db.flush()

        return product

    # =====================================================
    # CATEGORY OPERATIONS
    # =====================================================

    def create_category(
        self,
        data: dict,
    ) -> Category:
        """Create a product category."""

        return self.categories.create(data)

    def get_category_by_id(
        self,
        category_id: int,
    ) -> Category | None:
        """Retrieve category by ID."""

        return self.db.get(Category, category_id)

    def get_category_by_slug(
        self,
        slug: str,
    ) -> Category | None:
        """Retrieve category using its slug."""

        statement = select(Category).where(
            Category.slug == slug
        )

        return self.db.scalars(statement).first()

    def get_all_categories(self) -> list[Category]:
        """Retrieve all categories in display order."""

        statement = (
            select(Category)
            .order_by(
                Category.display_order.asc(),
                Category.name.asc(),
            )
        )

        return list(self.db.scalars(statement).all())

    def get_root_categories(self) -> list[Category]:
        """Retrieve categories without a parent."""

        statement = (
            select(Category)
            .where(Category.parent_id.is_(None))
            .order_by(Category.display_order.asc())
        )

        return list(self.db.scalars(statement).all())

    def get_category_children(
        self,
        category_id: int,
    ) -> list[Category]:
        """Retrieve immediate child categories."""

        statement = (
            select(Category)
            .where(Category.parent_id == category_id)
            .order_by(Category.display_order.asc())
        )

        return list(self.db.scalars(statement).all())

    def update_category(
        self,
        category_id: int,
        data: dict,
    ) -> Category | None:
        """Update a category."""

        category = self.get_category_by_id(category_id)

        if category is None:
            return None

        return self.categories.update(category, data)

    # =====================================================
    # BRAND OPERATIONS
    # =====================================================

    def create_brand(
        self,
        data: dict,
    ) -> Brand:
        """Create a product brand."""

        return self.brands.create(data)

    def get_brand_by_id(
        self,
        brand_id: int,
    ) -> Brand | None:
        """Retrieve brand by ID."""

        return self.db.get(Brand, brand_id)

    def get_brand_by_slug(
        self,
        slug: str,
    ) -> Brand | None:
        """Retrieve brand using its slug."""

        statement = select(Brand).where(
            Brand.slug == slug
        )

        return self.db.scalars(statement).first()

    def get_all_brands(self) -> list[Brand]:
        """Retrieve all brands alphabetically."""

        statement = select(Brand).order_by(
            Brand.name.asc()
        )

        return list(self.db.scalars(statement).all())

    def update_brand(
        self,
        brand_id: int,
        data: dict,
    ) -> Brand | None:
        """Update a brand."""

        brand = self.get_brand_by_id(brand_id)

        if brand is None:
            return None

        return self.brands.update(brand, data)

    # =====================================================
    # PRODUCT IMAGE OPERATIONS
    # =====================================================

    def create_product_image(
        self,
        product_id: int,
        data: dict,
    ) -> ProductImage:
        """Add an image to a product."""

        image_data = data.copy()
        image_data["product_id"] = product_id

        return self.images.create(image_data)

    def get_product_images(
        self,
        product_id: int,
    ) -> list[ProductImage]:
        """Retrieve images belonging to a product."""

        statement = (
            select(ProductImage)
            .where(ProductImage.product_id == product_id)
            .order_by(
                ProductImage.display_order.asc(),
                ProductImage.id.asc(),
            )
        )

        return list(self.db.scalars(statement).all())

    def delete_product_image(
        self,
        image_id: int,
    ) -> bool:
        """Delete a product image."""

        return self.images.delete_by_id(image_id)

    # =====================================================
    # PRODUCT VARIANT OPERATIONS
    # =====================================================

    def create_product_variant(
        self,
        product_id: int,
        data: dict,
    ) -> ProductVariant:
        """Add a variant to a product."""

        variant_data = data.copy()
        variant_data["product_id"] = product_id

        return self.variants.create(variant_data)

    def get_product_variants(
        self,
        product_id: int,
    ) -> list[ProductVariant]:
        """Retrieve variants belonging to a product."""

        statement = (
            select(ProductVariant)
            .where(ProductVariant.product_id == product_id)
            .order_by(ProductVariant.name.asc())
        )

        return list(self.db.scalars(statement).all())

    def get_variant_by_id(
        self,
        variant_id: int,
    ) -> ProductVariant | None:
        """Retrieve a product variant by ID."""

        return self.db.get(ProductVariant, variant_id)

    # =====================================================
    # CATALOGUE COUNTS
    # =====================================================

    def count_products(self) -> int:
        """Return total number of products."""

        return self.products.count()

    def count_published_products(self) -> int:
        """Return the number of published and active products."""

        statement = (
            select(func.count(Product.id))
            .where(
                Product.is_published.is_(True),
                Product.is_active.is_(True),
            )
        )

        return self.db.scalar(statement) or 0

    def count_categories(self) -> int:
        """Return total number of categories."""

        return self.categories.count()

    def count_brands(self) -> int:
        """Return total number of brands."""

        return self.brands.count()
