"""Shared time helpers for consistent UTC handling across the app."""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.types import DateTime, TypeDecorator


def utc_now() -> datetime:
    """Return the current time as a timezone-aware UTC datetime."""
    return datetime.now(UTC)


def ensure_utc(value: datetime | None) -> datetime | None:
    """Normalize a datetime to timezone-aware UTC."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def parse_utc_datetime(value: str | datetime | None) -> datetime | None:
    """Parse ISO timestamps and normalize them to timezone-aware UTC."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return ensure_utc(value)

    normalized = value.replace("Z", "+00:00")
    return ensure_utc(datetime.fromisoformat(normalized))


def utc_isoformat(value: datetime | None) -> str | None:
    """Serialize a datetime as an ISO-8601 UTC timestamp."""
    normalized = ensure_utc(value)
    if normalized is None:
        return None
    return normalized.isoformat().replace("+00:00", "Z")


class UTCDateTime(TypeDecorator[datetime]):
    """SQLAlchemy type that returns timezone-aware UTC datetimes on read."""

    impl = DateTime
    cache_ok = True

    def load_dialect_impl(self, dialect):
        return dialect.type_descriptor(DateTime(timezone=False))

    def process_bind_param(self, value: datetime | None, dialect):
        normalized = ensure_utc(value)
        if normalized is None:
            return None
        return normalized.replace(tzinfo=None)

    def process_result_value(self, value: datetime | None, dialect):
        return ensure_utc(value)