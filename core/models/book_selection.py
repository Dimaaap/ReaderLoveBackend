from typing import TYPE_CHECKING
from datetime import datetime

from sqlalchemy import Text, String, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .books import Book


class BookSelection(Base):
    __tablename__ = "book_selections"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    author_name: Mapped[str] = mapped_column(
        String(255), default="Редакція ExLove", nullable=False
    )
    cover_image: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    books: Mapped[list["Book"]] = relationship(
        secondary="book_selection_association", back_populates="selections"
    )

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(title={self.title}, slug={self.slug})"
