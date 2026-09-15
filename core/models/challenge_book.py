from typing import TYPE_CHECKING
from datetime import datetime

from sqlalchemy import Integer, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.models.base import Base

if TYPE_CHECKING:
    from .books import Book
    from .challenge import Challenge


class ChallengeBook(Base):
    __tablename__ = "challenge_books"

    challenge_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("challenges.id", ondelete="CASCADE"),
        primary_key=True,
    )

    book_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("books.id", ondelete="CASCADE"), primary_key=True
    )

    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    challenge: Mapped["Challenge"] = relationship(
        "Challenge", back_populates="challenge_books"
    )
    book: Mapped["Book"] = relationship("Book", back_populates="challenge_books")

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(challenge_id={self.challenge_id}, book_id={self.book_id})"
