from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class AuthorBookAssociation(Base):
    __tablename__ = "author_book_association"

    book_id: Mapped[int] = mapped_column(
        ForeignKey("books.id", ondelete="CASCADE"),
        primary_key=True,
    )
    author_id: Mapped[int] = mapped_column(
        ForeignKey("book_authors.id", ondelete="CASCADE"),
        primary_key=True,
    )
