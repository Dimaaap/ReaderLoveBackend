"""rename_register_ways_enum

Revision ID: 8d5a9058a379
Revises: 95a06b6e6324
Create Date: 2026-06-16 22:12:21.566177

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "8d5a9058a379"
down_revision: Union[str, Sequence[str], None] = "95a06b6e6324"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TYPE register_ways RENAME TO registerways")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("ALTER TYPE registerways RENAME TO register_ways")
