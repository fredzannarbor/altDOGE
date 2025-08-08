"""
Utility functions for CFR Document Analyzer.
"""

import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime


logger = logging.getLogger(__name__)


def safe_json_loads(json_str: Optional[str], default: Any = None) -> Any:
    """
    Safely parse JSON string with fallback.
    
    Args:
        json_str: JSON string to parse
        default: Default value if parsing fails
        
    Returns:
        Parsed JSON or default value
    """
    if not json_str:
        return default
    
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError) as e:
        logger.warning(f"Failed to parse JSON: {e}")
        return default


def safe_json_dumps(obj: Any, default: str = "[]") -> str:
    """
    Safely serialize object to JSON string.
    
    Args:
        obj: Object to serialize
        default: Default value if serialization fails
        
    Returns:
        JSON string or default value
    """
    try:
        return json.dumps(obj, ensure_ascii=False, indent=None)
    except (TypeError, ValueError) as e:
        logger.warning(f"Failed to serialize to JSON: {e}")
        return default


def truncate_text(text: str, max_length: int = 4000) -> str:
    """
    Truncate text to maximum length.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length] + "... [truncated]"


def format_timestamp(dt: Optional[datetime] = None) -> str:
    """
    Format timestamp for filenames and display.
    
    Args:
        dt: Datetime object (defaults to now)
        
    Returns:
        Formatted timestamp string
    """
    if dt is None:
        dt = datetime.now()
    
    return dt.strftime("%Y%m%d_%H%M%S")


def clean_filename(filename: str) -> str:
    """
    Clean filename by removing invalid characters.
    
    Args:
        filename: Original filename
        
    Returns:
        Cleaned filename
    """
    # Replace invalid characters with underscores
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Remove multiple consecutive underscores
    while '__' in filename:
        filename = filename.replace('__', '_')
    
    return filename.strip('_')


def extract_agency_name(agency_slug: str) -> str:
    """
    Convert agency slug to readable name.
    
    Args:
        agency_slug: Agency slug (e.g., 'securities-and-exchange-commission')
        
    Returns:
        Readable agency name
    """
    return agency_slug.replace('-', ' ').title()