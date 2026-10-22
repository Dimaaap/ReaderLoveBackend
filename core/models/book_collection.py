from typing import TYPE_CHECKING
from datetime import datetime

from .base import Base

from sqlalchemy import String, Text, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from .users import User
    from .books import Book


class BookCollection(Base):
    __tablename__ = "book_collections"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_public: Mapped[bool] = mapped_column(
        default=True, server_default="true", nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_defeault=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user: Mapped["User"] = relationship("User", back_populates="book_collections")
    books: Mapped[list["Book"]] = relationship(
        secondary="book_collection_association",
        back_populates="book_collections",
    )

    def __str__(self) -> str:
        return (
            f"{self.__class__.__name__}(title={self.title}, is_public={self.is_public})"
        )
