"""add updated_at audit triggers

Revision ID: updated_at_triggers_229
Revises: outbox_event_table_rev
Create Date: 2026-07-24 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "updated_at_triggers_229"
down_revision = "outbox_event_table_rev"
branch_labels = None
depends_on = None

UPDATED_AT_TABLES = (
    "user",
    "position",
    "airdrop",
    "telegram_user",
    "vault",
    "transaction",
    "extra_deposits",
    "event_outbox",
)


def _trigger_name(table_name: str) -> str:
    return f"set_{table_name}_updated_at"


def upgrade() -> None:
    for table_name in ("user", "position", "airdrop"):
        op.add_column(
            table_name,
            sa.Column(
                "updated_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION set_updated_at()
        RETURNS trigger AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    for table_name in UPDATED_AT_TABLES:
        op.execute(
            f"""
            DROP TRIGGER IF EXISTS {_trigger_name(table_name)} ON "{table_name}";
            CREATE TRIGGER {_trigger_name(table_name)}
            BEFORE UPDATE ON "{table_name}"
            FOR EACH ROW
            EXECUTE FUNCTION set_updated_at();
            """
        )


def downgrade() -> None:
    for table_name in reversed(UPDATED_AT_TABLES):
        op.execute(
            f'DROP TRIGGER IF EXISTS {_trigger_name(table_name)} ON "{table_name}";'
        )

    op.execute("DROP FUNCTION IF EXISTS set_updated_at();")

    for table_name in ("airdrop", "position", "user"):
        op.drop_column(table_name, "updated_at")