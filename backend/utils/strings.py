
"""String formatting utilities."""

import re
import unicodedata


def normalize_text(value: str) -> str:
    """Remove extra whitespace and normalize text."""
    return " ".join(value.strip().split())


def generate_slug(value: str) -> str:
    """Generate a URL-friendly slug."""
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode(
        "ascii",
        "ignore",
    ).decode("ascii")

    slug = ascii_text.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")

    if not slug:
        raise ValueError("Cannot generate a slug from empty text.")

    return slug


def truncate_text(
    value: str,
    max_length: int,
) -> str:
    """Truncate text to a maximum length."""
    if max_length < 0:
        raise ValueError("Maximum length cannot be negative.")

    return value[:max_length]
