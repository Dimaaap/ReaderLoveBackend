"""Changed id field type in reading_sessions table

Revision ID: c20b84cf2acc
Revises: 7af4fa6a2b34
Create Date: 2026-07-06 11:48:10.958318

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "c20b84cf2acc"
down_revision: Union[str, Sequence[str], None] = "7af4fa6a2b34"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SEQUENCE IF NOT EXISTS reading_sessions_id_seq")

    op.execute(
        "ALTER TABLE reading_sessions ALTER COLUMN id TYPE INTEGER "
        "USING nextval('reading_sessions_id_seq')::integer"
    )

    op.execute("ALTER SEQUENCE reading_sessions_id_seq OWNED BY reading_sessions.id")
    op.execute(
        "ALTER TABLE reading_sessions ALTER COLUMN id SET DEFAULT nextval('reading_sessions_id_seq')"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("ALTER TABLE reading_sessions ALTER COLUMN id DROP DEFAULT")
    op.execute("DROP SEQUENCE IF EXISTS reading_sessions_id_seq")

    op.execute(
        "ALTER TABLE reading_sessions ALTER COLUMN id TYPE VARCHAR(21) "
        "USING id::varchar"
    )
