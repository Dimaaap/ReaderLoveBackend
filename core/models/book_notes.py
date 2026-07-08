from typing import TYPE_CHECKING
from enum import Enum
from datetime import datetime
import os

from sqlalchemy import (
    String,
    DateTime,
    Integer,
    ForeignKey,
    Boolean,
    Text,
    Enum as SqlEnum,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .users import User
    from .books import Book


class NoteCategory(str, Enum):
    THOUGHTS = "Думки"
    FAVORITE_QUOTES = "Улюблені цитати"
    SUMMARY = "Підсумки"


class BookNotes(Base):
    __tablename__ = "book_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    user_id: Mapped[str] = mapped_column(
        String(int(os.getenv("NANOID_KEY_SIZE"))),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    book_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("books.id", ondelete="CASCADE"), nullable=False, index=True
    )

    note_text: Mapped[str] = mapped_column(Text, nullable=False)
    note_category: Mapped[NoteCategory] = mapped_column(
        SqlEnum(NoteCategory, values_callable=lambda enum: [e.value for e in enum]),
        default=NoteCategory.FAVORITE_QUOTES,
        server_default=NoteCategory.FAVORITE_QUOTES.value,
        nullable=False,
    )

    is_important: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="0"
    )
    book_page: Mapped[int] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="notes")
    book: Mapped["Book"] = relationship("Book", back_populates="notes")

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(note_text={self.note_text}, note_category={self.note_category})"
