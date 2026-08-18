from typing import TYPE_CHECKING

from .base import Base

from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from .books import Book


class BookAuthors(Base):
    __tablename__ = "book_authors"

    __table_args__ = (
        UniqueConstraint(
            "first_name",
            "last_name",
            name="uq_book_authors_first_name_last_name",
        ),
    )

    first_name: Mapped[str] = mapped_column(String(255), nullable=True)
    last_name: Mapped[str] = mapped_column(String(255), nullable=True)
    slug: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )

    books: Mapped[list["Book"]] = relationship(
        secondary="author_book_association", back_populates="authors"
    )

    def __str__(self):
        return f"{self.__class__.__name__}(first_name={self.first_name}, last_name={self.last_name})"

    def get_author_name(self):
        return f"{self.first_name} {self.last_name}"
