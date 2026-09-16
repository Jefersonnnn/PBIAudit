"""
Initial migration with core tables
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create initial tables"""

    # Users table
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(255), nullable=False, unique=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("is_admin", sa.Boolean(), default=False),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("last_activity_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Workspaces table
    op.create_table(
        "workspaces",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("workspace_id", sa.String(255), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_premium", sa.Boolean(), default=False),
        sa.Column("state", sa.String(50), default="ACTIVE"),
        sa.Column("is_on_dedicated_capacity", sa.Boolean(), default=False),
        sa.Column("capacity_id", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(), default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Datasets table
    op.create_table(
        "datasets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("dataset_id", sa.String(255), nullable=False, unique=True),
        sa.Column("workspace_id", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("refresh_count", sa.Integer(), default=0),
        sa.Column("last_refresh_time", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Reports table
    op.create_table(
        "reports",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("report_id", sa.String(255), nullable=False, unique=True),
        sa.Column("workspace_id", sa.String(255), nullable=False),
        sa.Column("dataset_id", sa.String(255), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_paginated", sa.Boolean(), default=False),
        sa.Column("web_url", sa.String(500), nullable=False),
        sa.Column("created_at", sa.DateTime(), default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Usage metrics table
    op.create_table(
        "usage_metrics",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("report_id", sa.String(255), nullable=False),
        sa.Column("workspace_id", sa.String(255), nullable=False),
        sa.Column("metric_date", sa.DateTime(), nullable=False),
        sa.Column("views", sa.Integer(), default=0),
        sa.Column("unique_viewers", sa.Integer(), default=0),
        sa.Column("created_at", sa.DateTime(), default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Activity events table
    op.create_table(
        "activity_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("event_id", sa.String(255), nullable=False, unique=True),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("activity", sa.String(100), nullable=False),
        sa.Column("resource_id", sa.String(255), nullable=True),
        sa.Column("resource_type", sa.String(50), nullable=True),
        sa.Column("resource_name", sa.String(255), nullable=True),
        sa.Column("event_time", sa.DateTime(), nullable=False),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), default=sa.func.now(), onupdate=sa.func.now()),
    )


def downgrade() -> None:
    """Drop all tables"""
    op.drop_table("activity_events")
    op.drop_table("usage_metrics")
    op.drop_table("reports")
    op.drop_table("datasets")
    op.drop_table("workspaces")
    op.drop_table("users")
