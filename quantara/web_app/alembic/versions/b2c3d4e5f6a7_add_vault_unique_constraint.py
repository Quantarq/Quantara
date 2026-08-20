"""Add unique constraint on vault(user_id, symbol)

Revision ID: b2c3d4e5f6a7
Revises: outbox_event_table_rev
Create Date: 2026-08-20

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b2c3d4e5f6a7"
down_revision = "outbox_event_table_rev"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Deduplicates vault rows then adds a unique constraint on (user_id, symbol)."""
    conn = op.get_bind()

    # Deduplicate: for each (user_id, symbol) pair keep only the row with the
    # latest updated_at and sum all amounts into it, then delete the rest.
    conn.execute(sa.text("""
        WITH ranked AS (
            SELECT id,
                   user_id,
                   symbol,
                   amount,
                   updated_at,
                   ROW_NUMBER() OVER (
                       PARTITION BY user_id, symbol ORDER BY updated_at DESC, id
                   ) AS rn
            FROM vault
        ),
        totals AS (
            SELECT user_id,
                   symbol,
                   SUM(amount::numeric) AS total_amount
            FROM vault
            GROUP BY user_id, symbol
        )
        UPDATE vault v
        SET amount = t.total_amount::text
        FROM totals t
        WHERE v.user_id = t.user_id
          AND v.symbol = t.symbol
          AND v.id IN (
              SELECT id FROM ranked WHERE rn > 1
          );

        DELETE FROM vault
        WHERE id IN (
            SELECT id FROM (
                SELECT id,
                       ROW_NUMBER() OVER (
                           PARTITION BY user_id, symbol ORDER BY updated_at DESC, id
                       ) AS rn
                FROM vault
            ) sub
            WHERE rn > 1
        );
    """))

    op.create_unique_constraint(
        "uq_vault_user_symbol", "vault", ["user_id", "symbol"]
    )


def downgrade() -> None:
    """Drops the unique constraint on vault(user_id, symbol)."""
    op.drop_constraint("uq_vault_user_symbol", "vault", type_="unique")
