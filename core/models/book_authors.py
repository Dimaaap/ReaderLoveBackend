from .base import Base

from sqlalchemy import String, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column


class BookAuthors(Base):
    __tablename__ = "book_authors"

    first_name: Mapped[str] = mapped_column(String(255), nullable=True)
    last_name: Mapped[str] = mapped_column(String(255), nullable=True)
    slug: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )

    def __str__(self):
        return f"{self.__class__.__name__}(first_name={self.first_name}, last_name={self.last_name})"
