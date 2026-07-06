from typing import TYPE_CHECKING

from .base import Base

from sqlalchemy import String, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from .book_authors import BookAuthors
    from .book_genres import BookGenres
    from .users import User
    from .reading_sessions import ReadingSession
    from .book_notes import BookNotes


class Book(Base):
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    image_link: Mapped[str] = mapped_column(String(255), nullable=True)
    pages_count: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[Text] = mapped_column(Text, nullable=True)
    publish_date: Mapped[str] = mapped_column(String(100), nullable=True)
    language: Mapped[str] = mapped_column(String(50), nullable=True)

    authors: Mapped[list["BookAuthors"]] = relationship(
        secondary="author_book_association", back_populates="books"
    )
    genres: Mapped[list["BookGenres"]] = relationship(
        secondary="genre_book_association", back_populates="books"
    )
    users: Mapped[list["User"]] = relationship(
        secondary="user_book_association", back_populates="books"
    )
    reading_sessions: Mapped[list["ReadingSession"]] = relationship(
        "ReadingSession", back_populates="book", cascade="all, delete-orphan"
    )

    notes: Mapped[list["BookNotes"]] = relationship(
        "BookNotes", back_populates="book", cascade="all, delete-orphan"
    )

    def __str__(self):
        return f"{self.__class__.__name__}(title={self.title}, slug={self.slug})"
