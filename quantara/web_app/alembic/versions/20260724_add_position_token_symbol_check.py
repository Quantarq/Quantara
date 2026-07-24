"""Add check constraint for supported position token symbols

Revision ID: token_symbol_check_230
Revises: outbox_event_table_rev
Create Date: 2026-07-24
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "token_symbol_check_230"
down_revision = "outbox_event_table_rev"
branch_labels = None
depends_on = None

CONSTRAINT_NAME = "ck_position_token_symbol_supported"
SUPPORTED_TOKENS = ("XLM", "USDC", "ETH", "WETH")


def upgrade() -> None:
    """Restrict position.token_symbol to supported assets."""
    token_list = ", ".join(f"'{token}'" for token in SUPPORTED_TOKENS)
    op.create_check_constraint(
        CONSTRAINT_NAME,
        "position",
        f"token_symbol IN ({token_list})",
    )


def downgrade() -> None:
    """Remove the supported-token check constraint."""
    op.drop_constraint(CONSTRAINT_NAME, "position", type_="check")