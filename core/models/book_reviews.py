from typing import TYPE_CHECKING
from datetime import datetime
import os

from sqlalchemy import (
    Text,
    String,
    Integer,
    DateTime,
    ForeignKey,
    CheckConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .books import Book
    from .users import User


class BookReview(Base):
    __tablename__ = "book_reviews"

    __table_args__ = (
        CheckConstraint("rating >=1 AND rating <=5", name="check_rating_range"),
    )

    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=True)

    book_id: Mapped[int] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"))
    user_id: Mapped[str] = mapped_column(
        String(int(os.getenv("NANOID_KEY_SIZE", 21))),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    book: Mapped["Book"] = relationship("Book", back_populates="reviews")
    user: Mapped["User"] = relationship("User", back_populates="reviews")

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(rating={self.rating}, text={self.text})"
