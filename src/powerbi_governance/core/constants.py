"""
Application constants - Centralized configuration values
"""

# ============================================================================
# POWER BI API CONSTANTS
# ============================================================================

POWERBI_API_VERSION = "v1.0"
POWERBI_SCOPES = [
    "https://analysis.windows.net/powerbi/api/.default"
]

# Default pagination
DEFAULT_PAGE_SIZE = 100
MAX_PAGE_SIZE = 5000

# Timeouts (seconds)
DEFAULT_HTTP_TIMEOUT = 30
XMLA_TIMEOUT = 60

# ============================================================================
# MICROSOFT GRAPH CONSTANTS
# ============================================================================

GRAPH_SCOPES = [
    "https://graph.microsoft.com/.default"
]

# ============================================================================
# DATABASE CONSTANTS
# ============================================================================

# SQLAlchemy
SQLALCHEMY_POOL_SIZE = 10
SQLALCHEMY_MAX_OVERFLOW = 20
SQLALCHEMY_POOL_RECYCLE = 3600
SQLALCHEMY_ECHO = False

# ============================================================================
# LOGGING CONSTANTS
# ============================================================================

LOG_LEVELS = {
    "DEBUG": 10,
    "INFO": 20,
    "WARNING": 30,
    "ERROR": 40,
    "CRITICAL": 50,
}

JSON_LOG_FORMAT = True
STRUCTLOG_PROCESSORS = [
    "structlog.stdlib.filter_by_level",
    "structlog.stdlib.add_logger_name",
    "structlog.stdlib.add_log_level",
    "structlog.stdlib.PositionalArgumentsFormatter",
    "structlog.processors.TimeStamper",
    "structlog.processors.StackInfoRenderer",
    "structlog.processors.format_exc_info",
    "structlog.processors.UnicodeDecoder",
    "structlog.processors.JSONRenderer",
]

# ============================================================================
# RETRY POLICY CONSTANTS
# ============================================================================

DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_FACTOR = 2
DEFAULT_INITIAL_DELAY = 1  # seconds

# HTTP Status codes to retry on
RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}

# ============================================================================
# ENTITY STATUS CONSTANTS
# ============================================================================

class EntityStatus:
    """Entity lifecycle status values"""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    ARCHIVED = "ARCHIVED"
    DELETED = "DELETED"


class UserStatus:
    """User status values"""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"
    GUEST = "GUEST"


class ReportStatus:
    """Report status values"""
    PUBLISHED = "PUBLISHED"
    DRAFT = "DRAFT"
    ARCHIVED = "ARCHIVED"


# ============================================================================
# PAGINATION
# ============================================================================

DEFAULT_PAGINATION_SIZE = 100
MAX_PAGINATION_SIZE = 5000

# ============================================================================
# CACHING
# ============================================================================

CACHE_TTL_SECONDS = 3600  # 1 hour
CACHE_WORKSPACE_TTL = 7200  # 2 hours
CACHE_DATASET_TTL = 1800  # 30 minutes

# ============================================================================
# DATE/TIME
# ============================================================================

TIMEZONE_UTC = "UTC"
TIMEZONE_DEFAULT = "UTC"

# ============================================================================
# SYNC JOBS
# ============================================================================

DEFAULT_SYNC_CRON = "0 2 * * *"  # 2 AM daily
SYNC_TIMEOUT_SECONDS = 600  # 10 minutes

# ============================================================================
# BATCH OPERATIONS
# ============================================================================

BATCH_SIZE = 100
BATCH_INSERT_SIZE = 500
BATCH_UPDATE_SIZE = 100

# ============================================================================
# VALIDATION
# ============================================================================

MIN_PASSWORD_LENGTH = 8
MAX_WORKSPACE_NAME_LENGTH = 200
MAX_DATASET_NAME_LENGTH = 200
MAX_REPORT_NAME_LENGTH = 200

# ============================================================================
# ERROR MESSAGES
# ============================================================================

ERROR_AUTHENTICATION_FAILED = "Authentication failed: Invalid credentials"
ERROR_WORKSPACE_NOT_FOUND = "Workspace not found"
ERROR_DATASET_NOT_FOUND = "Dataset not found"
ERROR_DATABASE_CONNECTION_FAILED = "Database connection failed"
ERROR_INVALID_REQUEST = "Invalid request parameters"
