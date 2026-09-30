"""
Domain enums - Enumeration types for domain concepts
"""

from enum import Enum


class EntityStatus(str, Enum):
    """Entity lifecycle status"""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    ARCHIVED = "ARCHIVED"
    DELETED = "DELETED"


class UserStatus(str, Enum):
    """User account status"""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"
    GUEST = "GUEST"


class WorkspaceState(str, Enum):
    """Workspace state in Power BI"""
    ACTIVE = "ACTIVE"
    DELETED = "DELETED"


class ReportType(str, Enum):
    """Power BI report types"""
    REPORT = "REPORT"
    USAGE_METRICS = "USAGE_METRICS"
    PAGINATED = "PAGINATED"
    EMBEDDED = "EMBEDDED"


class DatasetRefreshType(str, Enum):
    """Dataset refresh types"""
    SCHEDULED = "SCHEDULED"
    ON_DEMAND = "ON_DEMAND"
    MANUAL = "MANUAL"


class LicenseType(str, Enum):
    """Power BI license types"""
    PRO = "PRO"
    PREMIUM = "PREMIUM"
    PREMIUM_PER_USER = "PREMIUM_PER_USER"
    EMBEDDED = "EMBEDDED"
    FREE = "FREE"


class ActivityType(str, Enum):
    """Activity types from audit logs"""
    VIEW_REPORT = "ViewReport"
    VIEW_DASHBOARD = "ViewDashboard"
    EDIT_REPORT = "EditReport"
    CREATE_REPORT = "CreateReport"
    DELETE_REPORT = "DeleteReport"
    SHARE_REPORT = "ShareReport"
    UPDATE_DATASET = "UpdateDataset"
    REFRESH_DATASET = "RefreshDataset"
    DELETE_DATASET = "DeleteDataset"
    CREATE_WORKSPACE = "CreateWorkspace"
    DELETE_WORKSPACE = "DeleteWorkspace"
    UPDATE_WORKSPACE = "UpdateWorkspace"
    ADD_USER_TO_WORKSPACE = "AddUserToWorkspace"
    REMOVE_USER_FROM_WORKSPACE = "RemoveUserFromWorkspace"


__all__ = [
    "EntityStatus",
    "UserStatus",
    "WorkspaceState",
    "ReportType",
    "DatasetRefreshType",
    "LicenseType",
    "ActivityType",
]
