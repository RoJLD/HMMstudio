"""Time utilities shared across the server modules."""

from __future__ import annotations

from datetime import datetime, timezone


def utcnow() -> datetime:
    """Return current UTC time as a naive datetime.

    Replaces the deprecated ``datetime.utcnow()``. We strip the tzinfo to
    preserve the existing SQLite storage shape: stored datetimes have always
    been naive, and a switch to tz-aware would change ``isoformat()`` output
    (e.g. for ``SettingsResponse.updated_at``) and risk comparison bugs with
    rows persisted before the change.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)
