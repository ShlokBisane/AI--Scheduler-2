"""
Time utilities for consistent India Standard Time handling.
"""

from datetime import datetime, timezone, timedelta

try:
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover - fallback when zoneinfo is unavailable
    ZoneInfo = None


def _get_ist_tz():
    if ZoneInfo is not None:
        try:
            return ZoneInfo("Asia/Kolkata")
        except Exception:
            pass
    return timezone(timedelta(hours=5, minutes=30))


IST_TZ = _get_ist_tz()


def now_ist() -> datetime:
    """Return current time in IST."""
    return datetime.now(IST_TZ)


def today_ist():
    """Return current date in IST."""
    return now_ist().date()
