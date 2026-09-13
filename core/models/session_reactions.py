from datetime import datetime
import os
from typing import TYPE_CHECKING

from sqlalchemy import String, Integer, ForeignKey, DateTime, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .users import User
    from .reading_sessions import ReadingSession


class SessionReaction(Base):
    __tablename__ = "session_reactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    session_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("reading_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user_id: Mapped[str] = mapped_column(
        String(int(os.getenv("NANOID_KEY_SIZE"))),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    emoji: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    session: Mapped["ReadingSession"] = relationship(
        "ReadingSession", back_populates="reactions"
    )
    user: Mapped["User"] = relationship("User")

    __table_args__ = (
        UniqueConstraint(
            "session_id", "user_id", "emoji", name="uq_session_user_emoji"
        ),
    )
