"""Drop unused datasets/reports tables, add job_title/department to users

Revision ID: 003_drop_unused_and_user_profile
Revises: 002_license_assignments
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '003_drop_unused_and_user_profile'
down_revision = '002_license_assignments'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Drop datasets/reports (never populated by any command) and add user profile columns."""

    op.drop_table("datasets")
    op.drop_table("reports")

    op.add_column("users", sa.Column("job_title", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("department", sa.String(255), nullable=True))


def downgrade() -> None:
    """Recreate datasets/reports and drop the user profile columns."""

    op.drop_column("users", "department")
    op.drop_column("users", "job_title")

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
