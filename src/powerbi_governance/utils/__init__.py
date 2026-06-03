"""
Utility functions and helpers
"""

from datetime import datetime, timedelta
from typing import List, Optional

import pytz


def get_date_range(days_back: int = 1) -> tuple[datetime, datetime]:
    """
    Get date range for the last N days.
    
    Args:
        days_back: Number of days to look back
        
    Returns:
        Tuple of (start_datetime, end_datetime) in UTC
    """
    now = datetime.now(tz=pytz.UTC)
    start = now - timedelta(days=days_back)
    return start, now


def format_datetime(dt: Optional[datetime]) -> str:
    """
    Format datetime for display.
    
    Args:
        dt: Datetime object
        
    Returns:
        Formatted datetime string
    """
    if not dt:
        return "N/A"
    return dt.isoformat()


def chunk_list(items: List, chunk_size: int) -> List[List]:
    """
    Split list into chunks.
    
    Args:
        items: List to split
        chunk_size: Size of each chunk
        
    Returns:
        List of chunks
    """
    return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]


def mask_email(email: str) -> str:
    """
    Mask email for display purposes.
    
    Args:
        email: Email address
        
    Returns:
        Masked email
    """
    if not email or "@" not in email:
        return "***"

    parts = email.split("@")
    local = parts[0]

    if len(local) <= 2:
        masked_local = "***"
    else:
        masked_local = local[0] + "*" * (len(local) - 2) + local[-1]

    return f"{masked_local}@{parts[1]}"


__all__ = [
    "get_date_range",
    "format_datetime",
    "chunk_list",
    "mask_email",
]
