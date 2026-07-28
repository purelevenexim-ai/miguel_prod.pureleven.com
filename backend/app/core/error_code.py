"""
Error Code Generator
─────────────────────
Generates short, unique diagnostic codes for errors.
Format: ERR-<timestamp>-<hash>
Example: ERR-1708589644-7F3A

When an error occurs, log it with a code that users can share for diagnosis.
"""

import hashlib
from datetime import datetime, timezone
from typing import Optional


def generate_error_code(
    error_msg: str,
    error_type: str = "UNKNOWN",
    context: Optional[dict] = None,
) -> str:
    """
    Generate a shareable error code.
    
    Args:
        error_msg: The error message
        error_type: Category (VALIDATION, AUTH, SERVER, DATABASE, etc)
        context: Extra context dict to include in hash
    
    Returns:
        Error code like "ERR-1708589644-A3F7"
    """
    now = datetime.now(timezone.utc)
    timestamp = int(now.timestamp())
    
    # Build hash input
    hash_input = f"{error_msg}|{error_type}"
    if context:
        hash_input += f"|{sorted(context.items())}"
    
    # Generate short hash (always 4 chars with padding)
    h = hashlib.md5(hash_input.encode()).hexdigest()[:4].upper().zfill(4)
    
    code = f"ERR-{timestamp}-{h}"
    return code


def parse_error_code(code: str) -> dict:
    """
    Parse an error code back to components.
    
    Args:
        code: Error code like "ERR-1708589644-A3F7"
    
    Returns:
        Dict with timestamp, hash, datetime
    """
    if not code.startswith("ERR-"):
        return {}
    
    parts = code.split("-")
    if len(parts) != 3:
        return {}
    
    try:
        timestamp = int(parts[1])
        dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        return {
            "code": code,
            "timestamp": timestamp,
            "hash": parts[2],
            "datetime": dt.isoformat(),
        }
    except (ValueError, IndexError):
        return {}
