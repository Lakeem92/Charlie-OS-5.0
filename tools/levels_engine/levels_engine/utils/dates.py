"""Date helpers."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def today_str() -> str:
    """YYYY-MM-DD in UTC."""
    return utcnow().strftime("%Y-%m-%d")


def iso_utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def date_n_days_ago(n: int) -> str:
    return (utcnow() - timedelta(days=n)).strftime("%Y-%m-%d")
