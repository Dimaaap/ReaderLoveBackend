from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .books import Book


class BookPublisher(Base):
    __tablename__ = "book_publishers"

    title: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)

    books: Mapped[list["Book"]] = relationship(
        "Book",
        back_populates="publisher",
    )

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(title={self.title})"
