"""add claimed_at to outbox_event

Revision ID: add_claimed_at_outbox_rev
Revises: outbox_event_table_rev
Create Date: 2026-08-20 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "add_claimed_at_outbox_rev"
down_revision = "outbox_event_table_rev"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "event_outbox",
        sa.Column(
            "claimed_at",
            sa.DateTime(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("event_outbox", "claimed_at")
