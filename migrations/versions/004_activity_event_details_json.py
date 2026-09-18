"""Change activity_events.details from Text to JSON

Revision ID: 004_activity_event_details_json
Revises: 003_drop_unused_and_user_profile
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '004_activity_event_details_json'
down_revision = '003_drop_unused_and_user_profile'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Store details as JSON instead of Text - psycopg2 can't adapt a Python dict to a Text
    column, so every activity event sync failed to persist as soon as it tried to insert a row."""

    op.alter_column(
        "activity_events",
        "details",
        type_=sa.JSON(),
        postgresql_using="details::json",
    )


def downgrade() -> None:
    """Revert details back to Text."""

    op.alter_column(
        "activity_events",
        "details",
        type_=sa.Text(),
        postgresql_using="details::text",
    )
