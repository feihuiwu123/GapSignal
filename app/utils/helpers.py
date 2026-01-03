"""
Utility functions for GapSignal system.
"""
import time
import json
import hashlib
import math
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
import decimal


def format_price(price: float, precision: int = 4) -> str:
    """
    Format price with appropriate precision.

    Args:
        price: Price value
        precision: Number of decimal places

    Returns:
        Formatted price string
    """
    if price is None:
        return "N/A"

    if price >= 1000:
        return f"{price:,.2f}"
    elif price >= 1:
        return f"{price:.{precision}f}"
    else:
        # For small prices, use more precision
        precision = max(precision, int(-math.log10(price)) + 2) if price > 0 else precision
        return f"{price:.{precision}f}"


def format_volume(volume: float) -> str:
    """
    Format volume with appropriate units.

    Args:
        volume: Volume value

    Returns:
        Formatted volume string
    """
    if volume is None:
        return "N/A"

    if volume >= 1_000_000_000:
        return f"${volume/1_000_000_000:.2f}B"
    elif volume >= 1_000_000:
        return f"${volume/1_000_000:.2f}M"
    elif volume >= 1_000:
        return f"${volume/1_000:.2f}K"
    else:
        return f"${volume:.2f}"


def format_percent(value: float, signed: bool = True) -> str:
    """
    Format percentage value.

    Args:
        value: Percentage value
        signed: Whether to include + sign for positive values

    Returns:
        Formatted percentage string
    """
    if value is None:
        return "N/A"

    sign = "+" if signed and value > 0 else ""
    return f"{sign}{value:.2f}%"


def calculate_change(old: float, new: float) -> float:
    """
    Calculate percentage change.

    Args:
        old: Old value
        new: New value

    Returns:
        Percentage change
    """
    if old == 0:
        return 0.0
    return ((new - old) / old) * 100


def timestamp_to_datetime(timestamp: int) -> datetime:
    """
    Convert timestamp to datetime.

    Args:
        timestamp: Timestamp in milliseconds

    Returns:
        Datetime object
    """
    return datetime.fromtimestamp(timestamp / 1000)


def datetime_to_timestamp(dt: datetime) -> int:
    """
    Convert datetime to timestamp in milliseconds.

    Args:
        dt: Datetime object

    Returns:
        Timestamp in milliseconds
    """
    return int(dt.timestamp() * 1000)


def get_time_ago(timestamp: int) -> str:
    """
    Get human-readable time ago string.

    Args:
        timestamp: Timestamp in milliseconds

    Returns:
        Time ago string
    """
    dt = timestamp_to_datetime(timestamp)
    now = datetime.now()
    diff = now - dt

    if diff.days > 365:
        years = diff.days // 365
        return f"{years} year{'s' if years > 1 else ''} ago"
    elif diff.days > 30:
        months = diff.days // 30
        return f"{months} month{'s' if months > 1 else ''} ago"
    elif diff.days > 0:
        return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    else:
        return "just now"


def safe_float(value: Any, default: float = 0.0) -> float:
    """
    Safely convert value to float.

    Args:
        value: Value to convert
        default: Default value if conversion fails

    Returns:
        Float value
    """
    if value is None:
        return default

    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    """
    Safely convert value to int.

    Args:
        value: Value to convert
        default: Default value if conversion fails

    Returns:
        Integer value
    """
    if value is None:
        return default

    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def dict_hash(data: Dict[str, Any]) -> str:
    """
    Generate hash for dictionary.

    Args:
        data: Dictionary to hash

    Returns:
        MD5 hash string
    """
    # Sort dictionary to ensure consistent hashing
    sorted_data = json.dumps(data, sort_keys=True, default=str)
    return hashlib.md5(sorted_data.encode()).hexdigest()


def filter_dict(data: Dict[str, Any], keys: List[str]) -> Dict[str, Any]:
    """
    Filter dictionary to only include specified keys.

    Args:
        data: Input dictionary
        keys: Keys to include

    Returns:
        Filtered dictionary
    """
    return {k: data[k] for k in keys if k in data}


def chunk_list(lst: List[Any], chunk_size: int) -> List[List[Any]]:
    """
    Split list into chunks.

    Args:
        lst: List to split
        chunk_size: Size of each chunk

    Returns:
        List of chunks
    """
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def retry_on_exception(func, max_attempts: int = 3, delay: float = 1.0,
                       exceptions: tuple = (Exception,)):
    """
    Retry decorator for functions that may fail.

    Args:
        func: Function to retry
        max_attempts: Maximum number of attempts
        delay: Delay between attempts in seconds
        exceptions: Exceptions to catch

    Returns:
        Wrapped function
    """
    def wrapper(*args, **kwargs):
        last_exception = None
        for attempt in range(max_attempts):
            try:
                return func(*args, **kwargs)
            except exceptions as e:
                last_exception = e
                if attempt < max_attempts - 1:
                    time.sleep(delay * (attempt + 1))  # Exponential backoff
                continue
        raise last_exception
    return wrapper


class Timer:
    """Simple timer context manager."""

    def __init__(self, name: str = "Task"):
        self.name = name
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, *args):
        elapsed = time.time() - self.start_time
        print(f"{self.name} completed in {elapsed:.2f} seconds")

    def elapsed(self) -> float:
        """Get elapsed time in seconds."""
        if self.start_time is None:
            return 0.0
        return time.time() - self.start_time