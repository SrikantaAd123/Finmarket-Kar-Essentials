
"""Seed Finmarket Kart Essentials grocery catalog into MySQL."""

from __future__ import annotations

import re
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database.connection import engine
from backend.models.catalog import Category, Product


# ============================================================
# 1. GROCERY CATEGORIES AND 80 PRODUCTS
# ============================================================

CATALOG = {
    "fruits-vegetables": {
        "name": "Fruits & Vegetables",
        "description": "Fresh fruits and farm-fresh vegetables.",
        "prefix": "FV",
        "items": [
            ("Fresh Apples", "1 kg", "180.00"),
            ("Bananas", "1 dozen", "60.00"),
            ("Fresh Oranges", "1 kg", "90.00"),
            ("Tomatoes", "1 kg", "40.00"),
            ("Potatoes", "1 kg", "35.00"),
            ("Onions", "1 kg", "45.00"),
            ("Fresh Carrots", "1 kg", "55.00"),
            ("Green Spinach", "1 bunch", "30.00"),
        ],
    },

    "dairy-eggs": {
        "name": "Dairy & Eggs",
        "description": "Milk, dairy products and fresh eggs.",
        "prefix": "DE",
        "items": [
            ("Fresh Full Cream Milk", "1 litre", "70.00"),
            ("Toned Milk", "1 litre", "58.00"),
            ("Fresh Paneer", "200 g", "95.00"),
            ("Natural Curd", "500 g", "45.00"),
            ("Salted Butter", "100 g", "60.00"),
            ("Cheddar Cheese", "200 g", "145.00"),
            ("Farm Fresh Eggs", "12 pieces", "90.00"),
            ("Plain Yogurt", "400 g", "65.00"),
        ],
    },

    "bakery": {
        "name": "Bakery",
        "description": "Fresh bread, biscuits and bakery essentials.",
        "prefix": "BK",
        "items": [
            ("White Sandwich Bread", "400 g", "45.00"),
            ("Whole Wheat Bread", "400 g", "55.00"),
            ("Burger Buns", "4 pieces", "50.00"),
            ("Chocolate Cookies", "200 g", "75.00"),
            ("Butter Biscuits", "200 g", "50.00"),
            ("Plain Cake", "250 g", "110.00"),
            ("Rusk Toast", "200 g", "65.00"),
            ("Multigrain Bread", "400 g", "75.00"),
        ],
    },

    "rice-grains": {
        "name": "Rice & Grains",
        "description": "Everyday rice, grains and cereals.",
        "prefix": "RG",
        "items": [
            ("Premium Basmati Rice", "1 kg", "145.00"),
            ("Sona Masoori Rice", "5 kg", "320.00"),
            ("Brown Rice", "1 kg", "110.00"),
            ("Idli Rice", "1 kg", "65.00"),
            ("Wheat Flour", "5 kg", "240.00"),
            ("Ragi Flour", "1 kg", "75.00"),
            ("Poha", "500 g", "55.00"),
            ("Oats", "500 g", "95.00"),
        ],
    },

    "pulses-lentils": {
        "name": "Pulses & Lentils",
        "description": "Protein-rich pulses, beans and lentils.",
        "prefix": "PL",
        "items": [
            ("Toor Dal", "1 kg", "155.00"),
            ("Moong Dal", "1 kg", "130.00"),
            ("Masoor Dal", "1 kg", "110.00"),
            ("Chana Dal", "1 kg", "95.00"),
            ("Urad Dal", "1 kg", "145.00"),
            ("Kabuli Chana", "1 kg", "125.00"),
            ("Rajma", "1 kg", "140.00"),
            ("Green Moong", "1 kg", "120.00"),
        ],
    },

    "snacks": {
        "name": "Snacks & Munchies",
        "description": "Chips, namkeen and everyday snacks.",
        "prefix": "SN",
        "items": [
            ("Classic Potato Chips", "100 g", "30.00"),
            ("Masala Potato Chips", "100 g", "35.00"),
            ("Salted Peanuts", "200 g", "65.00"),
            ("Mixture Namkeen", "200 g", "70.00"),
            ("Roasted Chana", "200 g", "55.00"),
            ("Chocolate Wafer", "100 g", "40.00"),
            ("Popcorn", "100 g", "45.00"),
            ("Cashew Nuts", "200 g", "220.00"),
        ],
    },

    "beverages": {
        "name": "Beverages",
        "description": "Juices, tea, coffee and refreshing drinks.",
        "prefix": "BV",
        "items": [
            ("Orange Fruit Juice", "1 litre", "110.00"),
            ("Mango Drink", "1 litre", "95.00"),
            ("Green Tea", "25 bags", "140.00"),
            ("Premium Coffee Powder", "200 g", "180.00"),
            ("Black Tea", "250 g", "120.00"),
            ("Coconut Water", "200 ml", "40.00"),
            ("Lemon Drink", "750 ml", "55.00"),
            ("Hot Chocolate Mix", "200 g", "160.00"),
        ],
    },

    "cooking-essentials": {
        "name": "Cooking Essentials",
        "description": "Oils, spices, salt and cooking ingredients.",
        "prefix": "CE",
        "items": [
            ("Sunflower Cooking Oil", "1 litre", "155.00"),
            ("Groundnut Oil", "1 litre", "190.00"),
            ("Refined Sugar", "1 kg", "48.00"),
            ("Iodized Salt", "1 kg", "25.00"),
            ("Turmeric Powder", "200 g", "55.00"),
            ("Red Chilli Powder", "200 g", "75.00"),
            ("Garam Masala", "100 g", "65.00"),
            ("Coriander Powder", "200 g", "60.00"),
        ],
    },

    "personal-care": {
        "name": "Personal Care",
        "description": "Daily hygiene and personal care essentials.",
        "prefix": "PC",
        "items": [
            ("Herbal Shampoo", "180 ml", "145.00"),
            ("Bathing Soap", "4 pieces", "110.00"),
            ("Toothpaste", "150 g", "95.00"),
            ("Toothbrush", "1 piece", "35.00"),
            ("Hand Wash", "200 ml", "75.00"),
            ("Body Lotion", "200 ml", "165.00"),
            ("Face Wash", "100 ml", "125.00"),
            ("Hair Oil", "200 ml", "110.00"),
        ],
    },

    "household": {
        "name": "Household Essentials",
        "description": "Cleaning and everyday household supplies.",
        "prefix": "HE",
        "items": [
            ("Dishwashing Liquid", "500 ml", "95.00"),
            ("Laundry Detergent", "1 kg", "125.00"),
            ("Floor Cleaner", "1 litre", "110.00"),
            ("Toilet Cleaner", "500 ml", "95.00"),
            ("Garbage Bags", "30 pieces", "85.00"),
            ("Kitchen Tissues", "2 rolls", "75.00"),
            ("Scrub Pads", "3 pieces", "40.00"),
            ("Fabric Softener", "500 ml", "120.00"),
        ],
    },
}


# ============================================================
# 2. HELPER FUNCTIONS
# ============================================================

def make_slug(value: str) -> str:
    """Convert product or category names into URL-friendly slugs."""

    slug = value.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")

    if not slug:
        raise ValueError("Cannot generate a slug from empty text.")

    return slug


# ============================================================
# 3. SEED CATEGORIES
# ============================================================

def seed_categories(db: Session) -> dict[str, int]:
    """Insert missing categories and return their database IDs."""

    category_ids: dict[str, int] = {}

    for display_order, (slug, category_data) in enumerate(
        CATALOG.items(),
        start=1,
    ):
        category = db.scalar(
            select(Category).where(Category.slug == slug)
        )

        if category is None:
            category = Category(
                name=category_data["name"],
                slug=slug,
                description=category_data["description"],
                display_order=display_order,
                is_active=True,
            )

            db.add(category)
            db.flush()

            print(f"Added category: {category.name}")
        else:
            print(f"Category already exists: {category.name}")

        category_ids[slug] = category.id

    return category_ids


# ============================================================
# 4. SEED PRODUCTS
# ============================================================

def seed_products(
    db: Session,
    category_ids: dict[str, int],
) -> tuple[int, int]:
    """Insert missing products using the Product ORM model."""

    inserted = 0
    skipped = 0

    for category_slug, category_data in CATALOG.items():
        category_id = category_ids[category_slug]
        prefix = category_data["prefix"]

        for index, item in enumerate(
            category_data["items"],
            start=1,
        ):
            name, unit, price = item

            slug = make_slug(name)
            sku = f"{prefix}-{index:03d}"

            existing = db.scalar(
                select(Product).where(
                    (Product.sku == sku)
                    | (Product.slug == slug)
                )
            )

            if existing is not None:
                skipped += 1
                print(f"Product already exists: {sku}")
                continue

            product = Product(
                category_id=category_id,
                name=name,
                slug=slug,
                sku=sku,
                short_description=f"{name} - {unit}",
                description=(
                    f"{name} - quality grocery product "
                    "from Finmarket Kart Essentials."
                ),
                price=Decimal(price),
                currency="INR",
                unit=unit,
                is_active=True,
                is_published=True,
                is_featured=False,
            )

            db.add(product)
            inserted += 1

            print(f"Added product: {name} ({sku})")

    return inserted, skipped


# ============================================================
# 5. MAIN SEED FUNCTION
# ============================================================

def seed_catalog() -> None:
    """Seed the Finmarket Kart grocery catalog."""

    print("\n==========================================")
    print(" FINMARKET KART ESSENTIALS")
    print(" GROCERY CATALOG SEEDING")
    print("==========================================\n")

    try:
        with Session(engine) as db:
            category_ids = seed_categories(db)

            inserted, skipped = seed_products(
                db,
                category_ids,
            )

            db.commit()

            total_products = inserted + skipped

            print("\n==========================================")
            print(" CATALOG SEEDING COMPLETED")
            print("==========================================")
            print(f"Categories processed: {len(category_ids)}")
            print(f"Products inserted: {inserted}")
            print(f"Products already present: {skipped}")
            print(f"Total products processed: {total_products}")
            print("==========================================\n")

    except Exception:
        print("\nCatalog seeding failed. Rolling back transaction.")

        raise


# ============================================================
# 6. SCRIPT ENTRY POINT
# ============================================================

if __name__ == "__main__":
    seed_catalog()
