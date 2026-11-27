
"""Public catalogue and administrator catalogue APIs."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.auth.dependencies import get_current_admin
from backend.database.connection import get_db
from backend.services.catalog_service import CatalogService

from backend.schemas.catalog import (
    CategoryCreate,
    CategoryUpdate,
    BrandCreate,
    BrandUpdate,
    ProductCreate,
    ProductUpdate,
    ProductFilter,
    ProductImageCreate,
    ProductVariantCreate,
)
from decimal import Decimal
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from backend.models.catalog import Product

router = APIRouter(
    prefix="/catalog",
    tags=["Product Catalogue"],
)


# =========================================================
# SERIALIZATION HELPERS
# =========================================================

def _fallback_category_image(category: Any) -> str:
    """Choose an existing local category image when no uploaded image exists."""
    name = str(getattr(category, "name", "") or "").lower()
    mappings = (
        (("fruit", "vegetable"), "/static/images/banners/fruits-vegetables.jpg"),
        (("dairy", "egg"), "/static/images/products/milk.jpg"),
        (("bakery", "bread"), "/static/images/products/bread.jpg"),
        (("rice", "grain"), "/static/images/products/rice.jpg"),
        (("pulse", "lentil"), "/static/images/products/toor-dal.jpg"),
        (("snack", "munch"), "/static/images/banners/snacks-beverages.jpg"),
        (("beverage", "drink"), "/static/images/banners/snacks-beverages.jpg"),
        (("cooking", "essential"), "/static/images/products/cooking-oil.jpg"),
        (("personal", "care"), "/static/images/categories/beauty-personal-care.jpg"),
        (("household",), "/static/images/categories/home-kitchen-living.jpg"),
    )
    for keywords, image_url in mappings:
        if any(keyword in name for keyword in keywords):
            return image_url
    return "/static/images/logo/finmarket-kart-essentials-icon.png"


def _serialize_category(category: Any) -> dict:
    return {
        "id": category.id,
        "name": category.name,
        "slug": category.slug,
        "description": category.description,
        "image_url": category.image_url or _fallback_category_image(category),
        "parent_id": category.parent_id,
        "display_order": category.display_order,
        "is_active": category.is_active,
        "created_at": category.created_at,
        "updated_at": category.updated_at,
    }


def _serialize_brand(brand: Any) -> dict:
    return {
        "id": brand.id,
        "name": brand.name,
        "slug": brand.slug,
        "description": brand.description,
        "logo_url": brand.logo_url,
        "is_active": brand.is_active,
        "created_at": brand.created_at,
        "updated_at": brand.updated_at,
    }


def _serialize_image(image: Any) -> dict:
    return {
        "id": image.id,
        "image_url": image.image_url,
        "alt_text": image.alt_text,
        "is_primary": image.is_primary,
        "display_order": image.display_order,
        "created_at": image.created_at,
        "updated_at": image.updated_at,
    }


def _serialize_variant(variant: Any) -> dict:
    return {
        "id": variant.id,
        "product_id": variant.product_id,
        "sku": variant.sku,
        "name": variant.name,
        "price": variant.price,
        "attributes": variant.attributes,
        "is_active": variant.is_active,
        "created_at": variant.created_at,
        "updated_at": variant.updated_at,
    }


def _fallback_product_image(product: Any) -> str:
    """
    Select a local catalogue image when a product has no uploaded image.

    The archive contains a limited set of sample grocery images. These
    are presentation fallbacks, not a claim that every item has its own
    product photograph. Upload an exact image later through the admin
    product-image endpoint to override this fallback.
    """
    name = str(getattr(product, "name", "") or "").lower()
    category = str(
        getattr(getattr(product, "category", None), "name", "") or ""
    ).lower()

    keyword_images = (
        (("apple", "orange"), "apple.jpg"),
        (("banana",), "banana.jpg"),
        (("tomato",), "tomato.jpg"),
        (("potato", "chips"), "potato.jpg"),
        (("onion",), "onion.jpg"),
        (("carrot",), "carrot.jpg"),
        (("spinach", "broccoli", "capsicum", "cauliflower"), "spinach.jpg"),
        (("milk", "paneer", "curd", "yogurt"), "milk.jpg"),
        (("butter", "cheese"), "butter.jpg"),
        (("egg",), "eggs.jpg"),
        (("bread", "bun", "cookie", "biscuit", "cake", "rusk", "toast"), "bread.jpg"),
        (("rice", "poha", "oat", "flour", "ragi"), "rice.jpg"),
        (("toor", "dal", "lentil", "chana", "rajma", "urad", "masoor"), "toor-dal.jpg"),
        (("moong",), "moong-dal.jpg"),
        (("oil",), "cooking-oil.jpg"),
        (("sugar", "salt", "turmeric", "chilli", "masala", "coriander"), "sugar.jpg"),
        (("tea", "coffee", "juice", "drink", "coconut water"), "tea.jpg"),
    )

    for keywords, filename in keyword_images:
        if any(keyword in name for keyword in keywords):
            return f"/static/images/products/{filename}"

    category_images = (
        ("fruit", "apple.jpg"),
        ("vegetable", "carrot.jpg"),
        ("dairy", "milk.jpg"),
        ("egg", "eggs.jpg"),
        ("bakery", "bread.jpg"),
        ("rice", "rice.jpg"),
        ("grain", "rice.jpg"),
        ("pulse", "toor-dal.jpg"),
        ("lentil", "toor-dal.jpg"),
        ("snack", "potato.jpg"),
        ("beverage", "tea.jpg"),
        ("cooking", "cooking-oil.jpg"),
        ("personal", "../categories/beauty-personal-care.jpg"),
        ("household", "../categories/home-kitchen-living.jpg"),
        ("home", "../categories/home-kitchen-living.jpg"),
    )

    for keyword, filename in category_images:
        if keyword in category:
            if filename.startswith("../"):
                return f"/static/images/{filename[3:]}"
            return f"/static/images/products/{filename}"

    return "/static/images/logo/finmarket-kart-essentials-icon.png"


def _serialize_product(product: Any) -> dict:
    images = list(getattr(product, "images", []) or [])
    primary_image = next(
        (image for image in images if image.is_primary),
        images[0] if images else None,
    )

    stored_image_url = (
        getattr(product, "image_url", None)
        or (primary_image.image_url if primary_image else None)
    )
    image_url = stored_image_url or _fallback_product_image(product)

    category = getattr(product, "category", None)
    brand = getattr(product, "brand", None)

    return {
        "id": product.id,
        "sku": product.sku,
        "name": product.name,
        "slug": product.slug,
        "short_description": product.short_description,
        "description": product.description,
        "category_id": product.category_id,
        "category_name": getattr(category, "name", None),
        "brand_id": product.brand_id,
        "brand_name": getattr(brand, "name", None),
        "price": product.price,
        "compare_at_price": product.compare_at_price,
        "currency": product.currency,
        "unit": product.unit,
        "stock_quantity": getattr(product, "stock_quantity", 0),
        "image_url": image_url,
        "primary_image_url": image_url,
        "weight_value": product.weight_value,
        "weight_unit": product.weight_unit,
        "is_active": product.is_active,
        "is_published": product.is_published,
        "is_featured": product.is_featured,
        "is_available": bool(product.is_active and product.is_published),
        "images": [
            _serialize_image(image)
            for image in images
        ],
        "variants": [
            _serialize_variant(variant)
            for variant in product.variants
        ],
        "created_at": product.created_at,
        "updated_at": product.updated_at,
    }


def _handle_catalog_error(
    db: Session,
    error: Exception,
) -> None:
    db.rollback()

    if isinstance(error, IntegrityError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A catalogue record with conflicting information already exists.",
        ) from error

    if isinstance(error, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Unable to complete the catalogue operation.",
    ) from error


# =========================================================
# PUBLIC CATEGORY APIs
# =========================================================

@router.get("/categories")
def list_categories(
    db: Session = Depends(get_db),
):
    """Return all categories."""

    categories = CatalogService(db).get_all_categories()

    return {
        "success": True,
        "categories": [
            _serialize_category(category)
            for category in categories
            if category.is_active
        ],
    }


@router.get("/categories/root")
def list_root_categories(
    db: Session = Depends(get_db),
):
    """Return categories without a parent category."""

    categories = CatalogService(db).get_root_categories()

    return {
        "success": True,
        "categories": [
            _serialize_category(category)
            for category in categories
            if category.is_active
        ],
    }


@router.get("/categories/{category_id}/children")
def list_category_children(
    category_id: int,
    db: Session = Depends(get_db),
):
    """Return child categories."""

    try:
        categories = CatalogService(db).get_category_children(
            category_id
        )

        return {
            "success": True,
            "categories": [
                _serialize_category(category)
                for category in categories
                if category.is_active
            ],
        }

    except ValueError as exc:
        _handle_catalog_error(db, exc)


@router.get("/categories/slug/{slug}")
def get_category_by_slug(
    slug: str,
    db: Session = Depends(get_db),
):
    """Find a category using its URL slug."""

    try:
        category = CatalogService(db).get_category_by_slug(slug)

        if not category.is_active:
            raise HTTPException(status_code=404, detail="Category not found.")

        return {
            "success": True,
            "category": _serialize_category(category),
        }

    except ValueError as exc:
        _handle_catalog_error(db, exc)


@router.get("/categories/{category_id}")
def get_category(
    category_id: int,
    db: Session = Depends(get_db),
):
    """Find a category using its ID."""

    try:
        category = CatalogService(db).get_category(category_id)

        if not category.is_active:
            raise HTTPException(status_code=404, detail="Category not found.")

        return {
            "success": True,
            "category": _serialize_category(category),
        }

    except ValueError as exc:
        _handle_catalog_error(db, exc)


# =========================================================
# PUBLIC BRAND APIs
# =========================================================

@router.get("/brands")
def list_brands(
    db: Session = Depends(get_db),
):
    """Return all active brands."""

    brands = CatalogService(db).get_all_brands()

    return {
        "success": True,
        "brands": [
            _serialize_brand(brand)
            for brand in brands
            if brand.is_active
        ],
    }


@router.get("/brands/slug/{slug}")
def get_brand_by_slug(
    slug: str,
    db: Session = Depends(get_db),
):
    """Find a brand using its URL slug."""

    try:
        brand = CatalogService(db).get_brand_by_slug(slug)

        if not brand.is_active:
            raise HTTPException(status_code=404, detail="Brand not found.")

        return {
            "success": True,
            "brand": _serialize_brand(brand),
        }

    except ValueError as exc:
        _handle_catalog_error(db, exc)


@router.get("/brands/{brand_id}")
def get_brand(
    brand_id: int,
    db: Session = Depends(get_db),
):
    """Find a brand using its ID."""

    try:
        brand = CatalogService(db).get_brand(brand_id)

        if not brand.is_active:
            raise HTTPException(status_code=404, detail="Brand not found.")

        return {
            "success": True,
            "brand": _serialize_brand(brand),
        }

    except ValueError as exc:
        _handle_catalog_error(db, exc)


# =========================================================
# PUBLIC PRODUCT APIs
# =========================================================

@router.get("/products")
def list_products(
    search: str | None = Query(default=None, max_length=150),
    category_id: int | None = Query(default=None, ge=1),
    brand_id: int | None = Query(default=None, ge=1),
   minimum_price: Decimal | None = Query(default=None, ge=0),
   maximum_price: Decimal | None = Query(default=None, ge=0),
    featured: bool | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    sort_by: str = Query(default="created_at", pattern="^(created_at|name|price)$"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
):
    """Search and filter published products."""

    try:
        filters = ProductFilter(
            search=search,
            category_id=category_id,
            brand_id=brand_id,
            minimum_price=minimum_price,
            maximum_price=maximum_price,
            is_featured=featured,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        products, total = CatalogService(db).search_products(
            search=filters.search,
            category_id=filters.category_id,
            brand_id=filters.brand_id,
            min_price=filters.minimum_price,
            max_price=filters.maximum_price,
            featured=filters.is_featured,
            page=page,
            page_size=page_size,
            sort_by=filters.sort_by,
            sort_order=filters.sort_order,
            published_only=True,
        )

        return {
            "success": True,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": (total + page_size - 1) // page_size,
            },
            "products": [
                _serialize_product(product)
                for product in products
            ],
        }

    except ValueError as exc:
        _handle_catalog_error(db, exc)


@router.get("/products/featured")
def list_featured_products(
    limit: int = Query(default=12, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Return featured products."""

    try:
        products = CatalogService(db).get_featured_products(limit)

        return {
            "success": True,
            "products": [
                _serialize_product(product)
                for product in products
            ],
        }

    except ValueError as exc:
        _handle_catalog_error(db, exc)


@router.get("/products/slug/{slug}")
def get_product_by_slug(
    slug: str,
    db: Session = Depends(get_db),
):
    """Retrieve a published product using its slug."""

    try:
        product = CatalogService(db).get_product_by_slug(slug)

        if not product.is_active or not product.is_published:
            raise HTTPException(status_code=404, detail="Product not found.")

        product = CatalogService(db).get_product_details(product.id)

        return {
            "success": True,
            "product": _serialize_product(product),
        }

    except ValueError as exc:
        _handle_catalog_error(db, exc)


@router.get("/products/category/{category_id}")
def list_products_by_category(
    category_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    Return products in a category.

    Clothes & Fashion (category 15):
    Include all active products, even if publication is pending.

    Other categories:
    Continue returning published and active products only.
    """
    try:
        if category_id == 15:
            conditions = [
                Product.category_id == category_id,
                Product.is_active.is_(True),
            ]

            total = db.scalar(
                select(func.count(Product.id)).where(*conditions)
            ) or 0

            statement = (
                select(Product)
                .options(
                    selectinload(Product.images),
                    selectinload(Product.variants),
                )
                .where(*conditions)
                .order_by(Product.created_at.desc(), Product.id.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )

            products = list(db.scalars(statement).all())

        else:
            products, total = CatalogService(db).get_products_by_category(
                category_id=category_id,
                page=page,
                page_size=page_size,
            )

            products = [
                product for product in products
                if product.is_active and product.is_published
            ]

        return {
            "success": True,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": (total + page_size - 1) // page_size,
            },
            "products": [
                _serialize_product(product)
                for product in products
            ],
        }

    except ValueError as exc:
        _handle_catalog_error(db, exc)

@router.get("/products/brand/{brand_id}")
def list_products_by_brand(
    brand_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Return published products belonging to a brand."""

    try:
        products, total = CatalogService(db).get_products_by_brand(
            brand_id=brand_id,
            page=page,
            page_size=page_size,
        )

        products = [
            product for product in products
            if product.is_active and product.is_published
        ]

        return {
            "success": True,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": (total + page_size - 1) // page_size,
            },
            "products": [
                _serialize_product(product)
                for product in products
            ],
        }

    except ValueError as exc:
        _handle_catalog_error(db, exc)


@router.get("/products/{product_id}")
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
):
    """Retrieve a published product and its images and variants."""

    try:
        product = CatalogService(db).get_product_details(product_id)

        if not product.is_active or not product.is_published:
            raise HTTPException(status_code=404, detail="Product not found.")

        return {
            "success": True,
            "product": _serialize_product(product),
        }

    except ValueError as exc:
        _handle_catalog_error(db, exc)


# =========================================================
# ADMIN CATEGORY MANAGEMENT
# =========================================================

@router.post("/admin/categories", status_code=status.HTTP_201_CREATED)
def create_category(
    payload: CategoryCreate,
    current_admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    try:
        category = CatalogService(db).create_category(payload)
        db.commit()
        db.refresh(category)

        return {
            "success": True,
            "message": "Category created successfully.",
            "category": _serialize_category(category),
        }

    except (ValueError, IntegrityError) as exc:
        _handle_catalog_error(db, exc)


@router.patch("/admin/categories/{category_id}")
def update_category(
    category_id: int,
    payload: CategoryUpdate,
    current_admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    try:
        category = CatalogService(db).update_category(
            category_id,
            payload,
        )
        db.commit()
        db.refresh(category)

        return {
            "success": True,
            "message": "Category updated successfully.",
            "category": _serialize_category(category),
        }

    except (ValueError, IntegrityError) as exc:
        _handle_catalog_error(db, exc)


# =========================================================
# ADMIN BRAND MANAGEMENT
# =========================================================

@router.post("/admin/brands", status_code=status.HTTP_201_CREATED)
def create_brand(
    payload: BrandCreate,
    current_admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    try:
        brand = CatalogService(db).create_brand(payload)
        db.commit()
        db.refresh(brand)

        return {
            "success": True,
            "message": "Brand created successfully.",
            "brand": _serialize_brand(brand),
        }

    except (ValueError, IntegrityError) as exc:
        _handle_catalog_error(db, exc)


@router.patch("/admin/brands/{brand_id}")
def update_brand(
    brand_id: int,
    payload: BrandUpdate,
    current_admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    try:
        brand = CatalogService(db).update_brand(brand_id, payload)
        db.commit()
        db.refresh(brand)

        return {
            "success": True,
            "message": "Brand updated successfully.",
            "brand": _serialize_brand(brand),
        }

    except (ValueError, IntegrityError) as exc:
        _handle_catalog_error(db, exc)


# =========================================================
# ADMIN PRODUCT MANAGEMENT
# =========================================================

@router.post("/admin/products", status_code=status.HTTP_201_CREATED)
def create_product(
    payload: ProductCreate,
    current_admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    try:
        product = CatalogService(db).create_product(payload)
        db.commit()

        product = CatalogService(db).get_product_details(product.id)

        return {
            "success": True,
            "message": "Product created successfully.",
            "product": _serialize_product(product),
        }

    except (ValueError, IntegrityError) as exc:
        _handle_catalog_error(db, exc)


@router.patch("/admin/products/{product_id}")
def update_product(
    product_id: int,
    payload: ProductUpdate,
    current_admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    try:
        product = CatalogService(db).update_product(
            product_id,
            payload,
        )
        db.commit()

        product = CatalogService(db).get_product_details(product.id)

        return {
            "success": True,
            "message": "Product updated successfully.",
            "product": _serialize_product(product),
        }

    except (ValueError, IntegrityError) as exc:
        _handle_catalog_error(db, exc)


@router.patch("/admin/products/{product_id}/deactivate")
def deactivate_product(
    product_id: int,
    current_admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    try:
        product = CatalogService(db).deactivate_product(product_id)
        db.commit()

        return {
            "success": True,
            "message": "Product deactivated successfully.",
            "product_id": product.id,
        }

    except (ValueError, IntegrityError) as exc:
        _handle_catalog_error(db, exc)


# =========================================================
# ADMIN PRODUCT IMAGES
# =========================================================

@router.post(
    "/admin/products/{product_id}/images",
    status_code=status.HTTP_201_CREATED,
)
def add_product_image(
    product_id: int,
    payload: ProductImageCreate,
    current_admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    try:
        image = CatalogService(db).add_product_image(
            product_id,
            payload,
        )
        db.commit()
        db.refresh(image)

        return {
            "success": True,
            "message": "Product image added successfully.",
            "image": _serialize_image(image),
        }

    except (ValueError, IntegrityError) as exc:
        _handle_catalog_error(db, exc)


@router.get("/products/{product_id}/images")
def list_product_images(
    product_id: int,
    db: Session = Depends(get_db),
):
    try:
        images = CatalogService(db).get_product_images(product_id)

        return {
            "success": True,
            "images": [
                _serialize_image(image)
                for image in images
            ],
        }

    except ValueError as exc:
        _handle_catalog_error(db, exc)


@router.delete("/admin/products/images/{image_id}")
def delete_product_image(
    image_id: int,
    current_admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    try:
        CatalogService(db).delete_product_image(image_id)
        db.commit()

        return {
            "success": True,
            "message": "Product image deleted successfully.",
        }

    except (ValueError, IntegrityError) as exc:
        _handle_catalog_error(db, exc)


# =========================================================
# ADMIN PRODUCT VARIANTS
# =========================================================

@router.post(
    "/admin/products/{product_id}/variants",
    status_code=status.HTTP_201_CREATED,
)
def add_product_variant(
    product_id: int,
    payload: ProductVariantCreate,
    current_admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    try:
        variant = CatalogService(db).add_product_variant(
            product_id,
            payload,
        )
        db.commit()
        db.refresh(variant)

        return {
            "success": True,
            "message": "Product variant added successfully.",
            "variant": _serialize_variant(variant),
        }

    except (ValueError, IntegrityError) as exc:
        _handle_catalog_error(db, exc)


@router.get("/products/{product_id}/variants")
def list_product_variants(
    product_id: int,
    db: Session = Depends(get_db),
):
    try:
        variants = CatalogService(db).get_product_variants(product_id)

        return {
            "success": True,
            "variants": [
                _serialize_variant(variant)
                for variant in variants
            ],
        }

    except ValueError as exc:
        _handle_catalog_error(db, exc)


# =========================================================
# ADMIN CATALOGUE STATISTICS
# =========================================================

@router.get("/admin/statistics")
def get_catalogue_statistics(
    current_admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return {
        "success": True,
        "statistics": CatalogService(db).get_catalogue_statistics(),
    }
