"""
SQLAlchemy ORM models for database persistence
"""

from datetime import datetime

from sqlalchemy import Column, Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class UserModel(Base):
    """User database model"""
    __tablename__ = "users"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(255), nullable=False, unique=True)
    email = Column(String(255), nullable=False, unique=True)
    display_name = Column(String(255), nullable=False)
    job_title = Column(String(255), nullable=True)
    department = Column(String(255), nullable=True)
    is_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    last_activity_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class WorkspaceModel(Base):
    """Workspace database model"""
    __tablename__ = "workspaces"

    id = Column(String(36), primary_key=True)
    workspace_id = Column(String(255), nullable=False, unique=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_premium = Column(Boolean, default=False)
    state = Column(String(50), default="ACTIVE")
    is_on_dedicated_capacity = Column(Boolean, default=False)
    capacity_id = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class UsageMetricModel(Base):
    """Usage metrics database model"""
    __tablename__ = "usage_metrics"

    id = Column(String(36), primary_key=True)
    report_id = Column(String(255), nullable=False)
    workspace_id = Column(String(255), nullable=False)
    metric_date = Column(DateTime, nullable=False)
    views = Column(Integer, default=0)
    unique_viewers = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class LicenseAssignmentModel(Base):
    """Power BI-related license assignment snapshot"""
    __tablename__ = "license_assignments"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    display_name = Column(String(255), nullable=False)
    license_type = Column(String(100), nullable=False)
    service_plan_name = Column(String(100), nullable=False)
    is_account_enabled = Column(Boolean, default=True)
    synced_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ActivityEventModel(Base):
    """Activity event database model"""
    __tablename__ = "activity_events"

    id = Column(String(36), primary_key=True)
    event_id = Column(String(255), nullable=False, unique=True)
    user_id = Column(String(255), nullable=False)
    activity = Column(String(100), nullable=False)
    resource_id = Column(String(255), nullable=True)
    resource_type = Column(String(50), nullable=True)
    resource_name = Column(String(255), nullable=True)
    event_time = Column(DateTime, nullable=False)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


__all__ = [
    "Base",
    "UserModel",
    "WorkspaceModel",
    "UsageMetricModel",
    "ActivityEventModel",
    "LicenseAssignmentModel",
]
