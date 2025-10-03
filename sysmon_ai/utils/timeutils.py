"""Time utilities for UTC/local conversions and parsing."""

import time
from datetime import datetime, timedelta, timezone
from typing import Optional, Union


def now_utc_ts() -> int:
    """Return current UTC timestamp in seconds."""
    return int(time.time())


def now_utc() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(timezone.utc)


def ts_to_utc(ts: int) -> datetime:
    """Convert Unix timestamp to UTC datetime."""
    return datetime.fromtimestamp(ts, tz=timezone.utc)


def ts_to_local(ts: int) -> datetime:
    """Convert Unix timestamp to local datetime."""
    return datetime.fromtimestamp(ts)


def parse_duration(duration: str) -> int:
    """
    Parse duration string to seconds.

    Args:
        duration: Duration string like '1h', '7d', '30m'

    Returns:
        Duration in seconds

    Examples:
        >>> parse_duration('1h')
        3600
        >>> parse_duration('7d')
        604800
    """
    units = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}
    duration = duration.strip().lower()

    if duration[-1] in units:
        try:
            value = int(duration[:-1])
            return value * units[duration[-1]]
        except ValueError:
            raise ValueError(f"Invalid duration format: {duration}")
    else:
        try:
            return int(duration)  # Assume seconds if no unit
        except ValueError:
            raise ValueError(f"Invalid duration format: {duration}")


def format_duration(seconds: Union[int, float]) -> str:
    """
    Format seconds into human-readable duration.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted string like '2d 3h 15m'
    """
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        return f"{seconds // 60}m"
    elif seconds < 86400:
        hours = seconds // 3600
        mins = (seconds % 3600) // 60
        return f"{hours}h {mins}m" if mins else f"{hours}h"
    else:
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        return f"{days}d {hours}h" if hours else f"{days}d"


def get_time_range(
    duration: str, end_ts: Optional[int] = None
) -> tuple[int, int]:
    """
    Get time range (start_ts, end_ts) for a given duration.

    Args:
        duration: Duration string like '1h', '7d'
        end_ts: End timestamp. If None, uses current time.

    Returns:
        Tuple of (start_ts, end_ts)
    """
    if end_ts is None:
        end_ts = now_utc_ts()
    start_ts = end_ts - parse_duration(duration)
    return start_ts, end_ts
