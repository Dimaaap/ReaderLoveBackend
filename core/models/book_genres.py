from typing import TYPE_CHECKING

from .base import Base

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from .books import Book


class BookGenres(Base):
    __tablename__ = "book_genres"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )
    description: Mapped[str] = mapped_column(Text, nullable=True)
    books: Mapped[list["Book"]] = relationship(
        secondary="genre_book_association", back_populates="genres"
    )

    def __str__(self):
        return f"{self.__class__.__name__}(title={self.title}, slug={self.slug})"
