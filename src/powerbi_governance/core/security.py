"""
Security utilities and primitives

Provides secure handling of sensitive data, token management, and security-related operations.
"""

from typing import Optional


def mask_secret(secret: Optional[str], visible_chars: int = 4) -> str:
    """
    Mask a secret for safe logging.
    
    Shows only the first N characters, masking the rest with asterisks.
    
    Args:
        secret: Secret string to mask
        visible_chars: Number of characters to show at the beginning
        
    Returns:
        Masked secret string
        
    Example:
        >>> mask_secret("my_super_secret_password", visible_chars=3)
        'my_*****'
    """
    if not secret:
        return "***"
    
    if len(secret) <= visible_chars:
        return "***"
    
    return secret[:visible_chars] + "*" * (len(secret) - visible_chars)


def mask_api_key(api_key: Optional[str]) -> str:
    """
    Mask an API key for safe logging.
    
    Args:
        api_key: API key to mask
        
    Returns:
        Masked API key
    """
    return mask_secret(api_key, visible_chars=3)


def mask_connection_string(conn_str: Optional[str]) -> str:
    """
    Mask a connection string for safe logging.
    
    Removes password or authentication tokens.
    
    Args:
        conn_str: Connection string to mask
        
    Returns:
        Masked connection string
    """
    if not conn_str:
        return "***"
    
    # Simple masking - replace password/token values
    masked = conn_str
    
    # Mask password in connection strings like "Password=xyz"
    if "Password=" in masked:
        parts = masked.split("Password=")
        if len(parts) > 1:
            # Find the next semicolon or end of string
            remaining = parts[1]
            next_delim = remaining.find(";")
            if next_delim == -1:
                masked = parts[0] + "Password=***"
            else:
                masked = parts[0] + "Password=***;" + remaining[next_delim + 1:]
    
    return masked


def mask_database_url(url: object) -> str:
    """
    Mask the password in a database URL for safe logging.

    Accepts a pydantic PostgresDsn/MultiHostUrl (e.g. Settings.database_url)
    rather than splitting the string, since splitting on "@" or ":" is easy
    to get backwards and leaves the password on the wrong side of the mask.
    Uses `.hosts()` because pydantic's DSN types support multiple hosts and
    don't expose a single flat `.username`/`.password`/`.port`.

    Args:
        url: A parsed database URL (e.g. Settings.database_url)

    Returns:
        The URL with every password replaced by "***", e.g.
        "postgresql+psycopg2://user:***@host:5432/db"
    """
    scheme = getattr(url, "scheme", None)
    hosts = getattr(url, "hosts", None)
    if scheme is None or not callable(hosts):
        return "***"

    rendered_hosts = []
    for host_info in hosts():
        username = host_info.get("username") or ""
        has_password = bool(host_info.get("password"))
        userinfo = f"{username}{':***' if has_password else ''}@" if username or has_password else ""

        host = host_info.get("host") or ""
        port = host_info.get("port")
        port_part = f":{port}" if port else ""

        rendered_hosts.append(f"{userinfo}{host}{port_part}")

    path = getattr(url, "path", None) or ""
    return f"{scheme}://{','.join(rendered_hosts)}{path}"


def is_valid_uuid(value: str) -> bool:
    """
    Validate if a string is a valid UUID.
    
    Args:
        value: String to validate
        
    Returns:
        True if valid UUID format, False otherwise
    """
    import uuid
    
    try:
        uuid.UUID(value)
        return True
    except (ValueError, AttributeError):
        return False
