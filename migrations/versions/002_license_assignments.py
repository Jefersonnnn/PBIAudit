"""Add license_assignments table

Revision ID: 002_license_assignments
Revises: 001_initial_schema
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '002_license_assignments'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create license_assignments table"""

    op.create_table(
        "license_assignments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("license_type", sa.String(100), nullable=False),
        sa.Column("service_plan_name", sa.String(100), nullable=False),
        sa.Column("is_account_enabled", sa.Boolean(), default=True),
        sa.Column("synced_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_license_assignments_email", "license_assignments", ["email"])


def downgrade() -> None:
    """Drop license_assignments table"""
    op.drop_index("ix_license_assignments_email", table_name="license_assignments")
    op.drop_table("license_assignments")
