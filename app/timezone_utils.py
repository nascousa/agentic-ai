"""
Timezone utilities for AgentManager Dashboard
All timestamps should be displayed in PST (Pacific Standard Time)
"""
from datetime import datetime, timezone, timedelta
from typing import Optional


def utc_to_pst(utc_dt: Optional[datetime]) -> Optional[datetime]:
    """
    Convert UTC datetime to PST (Pacific Standard Time)
    
    Args:
        utc_dt: UTC datetime object or None
        
    Returns:
        PST datetime object or None if input was None
    """
    if utc_dt is None:
        return None
    
    # PST is UTC-8
    pst_timezone = timezone(timedelta(hours=-8))
    
    # If datetime is naive, assume it's UTC
    if utc_dt.tzinfo is None:
        utc_dt = utc_dt.replace(tzinfo=timezone.utc)
    
    return utc_dt.astimezone(pst_timezone)


def format_pst_timestamp(dt: Optional[datetime]) -> str:
    """
    Format datetime as PST string in format: YYYY-MM-DD HH:MM:SS PST
    
    Args:
        dt: Datetime object (UTC or timezone-aware)
        
    Returns:
        Formatted PST timestamp string or "N/A" if dt is None
    """
    if dt is None:
        return "N/A"
    
    pst_dt = utc_to_pst(dt)
    if pst_dt is None:
        return "N/A"
    
    return pst_dt.strftime('%Y-%m-%d %H:%M:%S PST')


def get_current_pst() -> datetime:
    """
    Get current datetime in PST timezone
    
    Returns:
        Current PST datetime
    """
    utc_now = datetime.now(timezone.utc)
    return utc_to_pst(utc_now)


def format_current_pst() -> str:
    """
    Get current PST timestamp as formatted string
    
    Returns:
        Current PST timestamp in format: YYYY-MM-DD HH:MM:SS PST
    """
    return format_pst_timestamp(datetime.now(timezone.utc))


# Constants for easy access
PST_FORMAT = '%Y-%m-%d %H:%M:%S PST'
PST_TIMEZONE = timezone(timedelta(hours=-8))  # PST is UTC-8