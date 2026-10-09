from datetime import datetime
import os
from typing import TYPE_CHECKING

from sqlalchemy import String, DateTime, Integer, Boolean, ForeignKey, func, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .users import User
    from .books import Book
    from .session_reactions import SessionReaction


class ReadingSession(Base):
    __tablename__ = "reading_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    user_id: Mapped[str] = mapped_column(
        String(int(os.getenv("NANOID_KEY_SIZE"))),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    book_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("books.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    paused_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    total_paused_duration: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )

    start_page: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    end_page: Mapped[int | None] = mapped_column(Integer, nullable=True)

    is_tracked: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="reading_sessions")
    book: Mapped["Book"] = relationship("Book", back_populates="reading_sessions")
    reactions: Mapped[list["SessionReaction"]] = relationship(
        "SessionReaction", back_populates="session", cascade="all, delete-orphan"
    )

    @property
    def is_paused(self) -> bool:
        return self.paused_at is not None

    @property
    def net_duration_seconds(self) -> int:
        end_time = self.ended_at or datetime.now(self.started_at.tzinfo)
        total_time = int((end_time - self.started_at).total_seconds())

        current_pause = 0
        if self.paused_at:
            current_pause = int((end_time - self.paused_at).total_seconds())

        return max(0, total_time - self.total_paused_duration - current_pause)

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(user_id={self.user_id}, book_id={self.book_id}, start_at={self.started_at})"
