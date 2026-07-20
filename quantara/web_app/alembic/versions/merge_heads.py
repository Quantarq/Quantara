"""Merge multiple migration heads

Revision ID: merge_heads_rev
Revises: outbox_event_table_rev, e8d2f3c4a1b0
Create Date: 2026-07-20 22:53:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "merge_heads_rev"
down_revision = ("outbox_event_table_rev", "e8d2f3c4a1b0")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
