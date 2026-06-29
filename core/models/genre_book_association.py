from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from .base import BaseWithoutId


class GenreBookAssociation(BaseWithoutId):
    __tablename__ = "genre_book_association"

    book_id: Mapped[int] = mapped_column(
        ForeignKey("books.id", ondelete="CASCADE"), primary_key=True
    )
    genre_id: Mapped[int] = mapped_column(
        ForeignKey("book_genres.id", ondelete="CASCADE"), primary_key=True
    )
