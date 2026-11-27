
"""Date and time utilities."""

from datetime import datetime, timezone


def utc_now() -> datetime:
    """Return the current UTC datetime."""
    return datetime.now(timezone.utc)


def ensure_utc(value: datetime) -> datetime:
    """Convert a datetime to UTC.

    Naive datetimes are interpreted as UTC.
    """
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


def is_expired(
    expires_at: datetime,
    current_time: datetime | None = None,
) -> bool:
    """Check whether a datetime has expired."""
    now = ensure_utc(current_time or utc_now())
    expiry = ensure_utc(expires_at)

    return expiry <= now
