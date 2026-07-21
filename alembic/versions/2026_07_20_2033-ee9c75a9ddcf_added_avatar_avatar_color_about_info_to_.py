"""Added avatar, avatar_color, about_info to users table

Revision ID: ee9c75a9ddcf
Revises: 16bb024eaeee
Create Date: 2026-07-20 20:33:33.301271
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM

# revision identifiers, used by Alembic.
revision: str = "ee9c75a9ddcf"
down_revision: Union[str, Sequence[str], None] = "16bb024eaeee"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


avatar_color_enum = ENUM(
    "pink",
    "purple",
    "blue",
    "green",
    "orange",
    "red",
    name="avatarcolors",
)


def upgrade() -> None:
    """Upgrade schema."""

    bind = op.get_bind()

    avatar_color_enum.create(bind, checkfirst=True)

    op.add_column(
        "users",
        sa.Column(
            "avatar",
            sa.String(length=255),
            nullable=True,
        ),
    )

    op.add_column(
        "users",
        sa.Column(
            "avatar_color",
            avatar_color_enum,
            nullable=False,
            server_default="pink",
        ),
    )

    op.add_column(
        "users",
        sa.Column(
            "about_info",
            sa.Text(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""

    bind = op.get_bind()

    op.drop_column("users", "about_info")
    op.drop_column("users", "avatar_color")
    op.drop_column("users", "avatar")

    avatar_color_enum.drop(bind, checkfirst=True)
