"""Opt-in utility to publish existing active FINMARKET products.

Run a dry-run first:
    uv run python -m backend.scripts.publish_active_catalog

Apply only after reviewing the count:
    uv run python -m backend.scripts.publish_active_catalog --apply
"""
from __future__ import annotations

import argparse

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from backend.database.connection import engine
from backend.models.catalog import Product


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Set is_published=True for active, non-deleted products.",
    )
    args = parser.parse_args()

    eligible = (
        Product.is_active.is_(True),
        Product.is_deleted.is_(False),
    )

    with Session(engine) as db:
        # Use a portable scalar count query.
        from sqlalchemy import func
        total = db.scalar(
            select(func.count(Product.id)).where(*eligible)
        ) or 0
        unpublished = db.scalar(
            select(func.count(Product.id)).where(
                *eligible, Product.is_published.is_(False)
            )
        ) or 0

        print(f"Active, non-deleted products: {total}")
        print(f"Currently unpublished: {unpublished}")

        if not args.apply:
            print("Dry run only. Re-run with --apply to publish these products.")
            return

        if unpublished == 0:
            print("No products need publishing.")
            return

        result = db.execute(
            update(Product)
            .where(*eligible, Product.is_published.is_(False))
            .values(is_published=True)
        )
        db.commit()

        published_count = getattr(result, "rowcount", None)

        if published_count is not None and published_count >= 0:
           
           print(f"Published {published_count} products.")

        else:
        
         print("Publishing completed. Affected row count is unavailable.")

         if __name__ == "__main__":
           main()
