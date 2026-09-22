from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from .base import BaseWithoutId


class BookSelectionAssociation(BaseWithoutId):
    __tablename__ = "book_selection_association"

    book_selection_id: Mapped[int] = mapped_column(
        ForeignKey("book_selections.id", ondelete="CASCADE"),
        primary_key=True,
    )

    book_id: Mapped[int] = mapped_column(
        ForeignKey("books.id", ondelete="CASCADE"), primary_key=True
    )
