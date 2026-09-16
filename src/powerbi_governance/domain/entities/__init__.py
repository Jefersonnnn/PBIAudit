"""
Domain entities - Core business objects
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class BaseEntity(BaseModel):
    """Base entity with common fields"""
    id: Optional[UUID] = Field(default=None, description="Entity unique identifier")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    
    class Config:
        """Entity configuration"""
        from_attributes = True


class User(BaseEntity):
    """Power BI user entity"""
    user_id: str = Field(description="Azure AD object ID")
    email: str = Field(description="User email address")
    display_name: str = Field(description="User display name")
    is_admin: bool = Field(default=False, description="Is Power BI admin")
    is_active: bool = Field(default=True, description="Is user active")
    last_activity_at: Optional[datetime] = Field(default=None, description="Last activity timestamp")


class Workspace(BaseEntity):
    """Power BI workspace entity"""
    workspace_id: str = Field(description="Workspace unique identifier from Power BI")
    name: str = Field(description="Workspace name")
    description: Optional[str] = Field(default=None, description="Workspace description")
    is_premium: bool = Field(default=False, description="Is Premium workspace")
    state: str = Field(default="ACTIVE", description="Workspace state")
    is_on_dedicated_capacity: bool = Field(default=False, description="On dedicated capacity")
    capacity_id: Optional[str] = Field(default=None, description="Capacity identifier if premium")


class Dataset(BaseEntity):
    """Power BI dataset entity"""
    dataset_id: str = Field(description="Dataset unique identifier from Power BI")
    workspace_id: str = Field(description="Parent workspace ID")
    name: str = Field(description="Dataset name")
    description: Optional[str] = Field(default=None, description="Dataset description")
    refresh_count: int = Field(default=0, description="Total refresh count")
    last_refresh_time: Optional[datetime] = Field(default=None, description="Last refresh timestamp")


class Report(BaseEntity):
    """Power BI report entity"""
    report_id: str = Field(description="Report unique identifier from Power BI")
    workspace_id: str = Field(description="Parent workspace ID")
    dataset_id: Optional[str] = Field(default=None, description="Linked dataset ID")
    name: str = Field(description="Report name")
    description: Optional[str] = Field(default=None, description="Report description")
    is_paginated: bool = Field(default=False, description="Is paginated report")
    web_url: str = Field(description="Web URL to report")


class UsageMetric(BaseEntity):
    """Usage metrics for Power BI items"""
    report_id: str = Field(description="Report ID")
    workspace_id: str = Field(description="Workspace ID")
    metric_date: datetime = Field(description="Date of metric")
    views: int = Field(default=0, description="Number of views")
    unique_viewers: int = Field(default=0, description="Number of unique viewers")


class LicenseAssignment(BaseEntity):
    """Power BI-related Microsoft 365 license assigned to a user"""
    user_id: str = Field(description="Azure AD object ID")
    email: str = Field(description="User email/UPN")
    display_name: str = Field(description="User display name")
    license_type: str = Field(description="Human-readable license name, e.g. 'Power BI Pro'")
    service_plan_name: str = Field(description="Raw Microsoft service plan identifier, e.g. 'BI_AZURE_P2'")
    is_account_enabled: bool = Field(default=True, description="Is the Azure AD account enabled")
    synced_at: datetime = Field(default_factory=datetime.utcnow, description="When this assignment was observed")


class ActivityEvent(BaseEntity):
    """Activity event from audit logs"""
    event_id: str = Field(description="Event unique identifier")
    user_id: str = Field(description="User who performed the action")
    activity: str = Field(description="Activity type")
    resource_id: Optional[str] = Field(default=None, description="Resource identifier")
    resource_type: Optional[str] = Field(default=None, description="Resource type")
    resource_name: Optional[str] = Field(default=None, description="Resource name")
    event_time: datetime = Field(description="Event timestamp")
    details: Optional[dict] = Field(default=None, description="Additional details")


__all__ = [
    "BaseEntity",
    "User",
    "Workspace",
    "Dataset",
    "Report",
    "UsageMetric",
    "ActivityEvent",
    "LicenseAssignment",
]
