from typing import TYPE_CHECKING

from .base import Base

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from .book_authors import BookAuthors


class Country(Base):
    __tablename__ = "countries"

    name: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True, index=True
    )
    name_uk: Mapped[str] = mapped_column(String(100), nullable=True, index=True)

    code: Mapped[str] = mapped_column(
        String(2), nullable=False, unique=True, index=True
    )

    flag: Mapped[str | None] = mapped_column(String(10), nullable=True)

    authors: Mapped[list["BookAuthors"]] = relationship(
        back_populates="country", passive_deletes=True
    )

    def __str__(self):
        return f"{self.__class__.__name__}(name={self.name}, flag={self.flag}, code={self.code})"
