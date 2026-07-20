"""create contract_audit table

Revision ID: e8d2f3c4a1b0
Revises: a10b2c3d4e5f
Create Date: 2026-07-20 16:30:00

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "e8d2f3c4a1b0"
down_revision = "a10b2c3d4e5f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Creates the contract_audit table with columns and foreign key."""
    op.create_table(
        "contract_audit",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("old_address", sa.String(), nullable=True),
        sa.Column("new_address", sa.String(), nullable=False),
        sa.Column("actor", sa.String(), nullable=True),
        sa.Column("request_id", sa.String(), nullable=True),
        sa.Column(
            "timestamp", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_contract_audit_user_id"),
        "contract_audit",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drops the contract_audit table and its index."""
    op.drop_index(op.f("ix_contract_audit_user_id"), table_name="contract_audit")
    op.drop_table("contract_audit")
