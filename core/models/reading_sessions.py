from datetime import datetime
import os
from typing import TYPE_CHECKING

from sqlalchemy import String, DateTime, Integer, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from utils.generate_nano import generate_nanoid
from .base import Base

if TYPE_CHECKING:
    from .users import User
    from .books import Book


class ReadingSession(Base):
    __tablename__ = "reading_sessions"

    id: Mapped[str] = mapped_column(
        String(int(os.getenv("NANOID_KEY_SIZE"))),
        primary_key=True,
        default=generate_nanoid,
    )

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

    start_page: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    end_page: Mapped[int | None] = mapped_column(Integer, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="reading_sessions")
    book: Mapped["Book"] = relationship("Book", back_populates="reading_sessions")

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(user_id={self.user_id}, book_id={self.book_id}, start_at={self.started_at})"
