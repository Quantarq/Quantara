"""migration: convert amount columns to Numeric(38,18)

Revision ID: 20230620_amount_numeric
Revises: b705d1435b64
Create Date: 2026-06-20 01:18:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20230620_amount_numeric'
down_revision = 'b705d1435b64'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Position.amount
    op.alter_column(
        'position',
        'amount',
        existing_type=sa.String(),
        type_=sa.Numeric(38, 18),
        postgresql_using='amount::numeric',
        nullable=False,
    )
    # ExtraDeposit.amount
    op.alter_column(
        'extra_deposits',
        'amount',
        existing_type=sa.String(),
        type_=sa.Numeric(38, 18),
        postgresql_using='amount::numeric',
        nullable=False,
    )
    # Vault.amount
    op.alter_column(
        'vault',
        'amount',
        existing_type=sa.String(),
        type_=sa.Numeric(38, 18),
        postgresql_using='amount::numeric',
        nullable=True,
    )


def downgrade() -> None:
    # Position.amount back to String
    op.alter_column(
        'position',
        'amount',
        existing_type=sa.Numeric(38, 18),
        type_=sa.String(),
        postgresql_using='amount::text',
        nullable=False,
    )
    # ExtraDeposit.amount back to String
    op.alter_column(
        'extra_deposits',
        'amount',
        existing_type=sa.Numeric(38, 18),
        type_=sa.String(),
        postgresql_using='amount::text',
        nullable=False,
    )
    # Vault.amount back to String (nullable)
    op.alter_column(
        'vault',
        'amount',
        existing_type=sa.Numeric(38, 18),
        type_=sa.String(),
        postgresql_using='amount::text',
        nullable=True,
    )
