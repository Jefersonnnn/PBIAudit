"""
Domain schemas - Pydantic models for data validation and serialization

These schemas represent DTOs (Data Transfer Objects) for API requests/responses
and data transformation across application layers.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class BaseSchema(BaseModel):
    """Base schema with common configuration"""
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None,
        }


# ============================================================================
# WORKSPACE SCHEMAS
# ============================================================================

class WorkspaceCreateSchema(BaseSchema):
    """Schema for creating a workspace"""
    name: str = Field(description="Workspace name")
    description: Optional[str] = Field(default=None, description="Workspace description")


class WorkspaceReadSchema(BaseSchema):
    """Schema for reading workspace data"""
    id: str = Field(description="Workspace ID")
    workspace_id: str = Field(description="Power BI workspace ID")
    name: str = Field(description="Workspace name")
    description: Optional[str] = Field(default=None)
    is_premium: bool = Field(default=False)
    state: str = Field(default="ACTIVE")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")


class WorkspaceUpdateSchema(BaseSchema):
    """Schema for updating a workspace"""
    name: Optional[str] = Field(default=None)
    description: Optional[str] = Field(default=None)


# ============================================================================
# DATASET SCHEMAS
# ============================================================================

class DatasetCreateSchema(BaseSchema):
    """Schema for creating a dataset"""
    workspace_id: str = Field(description="Parent workspace ID")
    name: str = Field(description="Dataset name")
    description: Optional[str] = Field(default=None)


class DatasetReadSchema(BaseSchema):
    """Schema for reading dataset data"""
    id: str = Field(description="Dataset ID")
    dataset_id: str = Field(description="Power BI dataset ID")
    workspace_id: str = Field(description="Workspace ID")
    name: str = Field(description="Dataset name")
    description: Optional[str] = Field(default=None)
    refresh_count: int = Field(default=0)
    last_refresh_time: Optional[datetime] = Field(default=None)


# ============================================================================
# REPORT SCHEMAS
# ============================================================================

class ReportCreateSchema(BaseSchema):
    """Schema for creating a report"""
    workspace_id: str = Field(description="Parent workspace ID")
    name: str = Field(description="Report name")
    description: Optional[str] = Field(default=None)
    web_url: str = Field(description="Report URL")


class ReportReadSchema(BaseSchema):
    """Schema for reading report data"""
    id: str = Field(description="Report ID")
    report_id: str = Field(description="Power BI report ID")
    workspace_id: str = Field(description="Workspace ID")
    dataset_id: Optional[str] = Field(default=None)
    name: str = Field(description="Report name")
    description: Optional[str] = Field(default=None)
    web_url: str = Field(description="Report URL")


# ============================================================================
# USER SCHEMAS
# ============================================================================

class UserReadSchema(BaseSchema):
    """Schema for reading user data"""
    id: str = Field(description="User ID")
    user_id: str = Field(description="Azure AD object ID")
    email: str = Field(description="User email")
    display_name: str = Field(description="User display name")
    is_admin: bool = Field(default=False)
    is_active: bool = Field(default=True)
    last_activity_at: Optional[datetime] = Field(default=None)


# ============================================================================
# USAGE METRICS SCHEMAS
# ============================================================================

class UsageMetricReadSchema(BaseSchema):
    """Schema for reading usage metrics"""
    id: str = Field(description="Metric ID")
    report_id: str = Field(description="Report ID")
    workspace_id: str = Field(description="Workspace ID")
    metric_date: datetime = Field(description="Metric date")
    views: int = Field(default=0)
    unique_viewers: int = Field(default=0)


# ============================================================================
# ACTIVITY EVENT SCHEMAS
# ============================================================================

class ActivityEventReadSchema(BaseSchema):
    """Schema for reading activity events"""
    id: str = Field(description="Event ID")
    event_id: str = Field(description="External event ID")
    user_id: str = Field(description="User ID")
    activity: str = Field(description="Activity type")
    resource_id: Optional[str] = Field(default=None)
    resource_type: Optional[str] = Field(default=None)
    resource_name: Optional[str] = Field(default=None)
    event_time: datetime = Field(description="Event timestamp")


# ============================================================================
# ERROR SCHEMAS
# ============================================================================

class ErrorSchema(BaseSchema):
    """Schema for error responses"""
    error_code: str = Field(description="Error code")
    message: str = Field(description="Error message")
    details: Optional[dict] = Field(default=None, description="Additional details")


__all__ = [
    "WorkspaceCreateSchema",
    "WorkspaceReadSchema",
    "WorkspaceUpdateSchema",
    "DatasetCreateSchema",
    "DatasetReadSchema",
    "ReportCreateSchema",
    "ReportReadSchema",
    "UserReadSchema",
    "UsageMetricReadSchema",
    "ActivityEventReadSchema",
    "ErrorSchema",
]
