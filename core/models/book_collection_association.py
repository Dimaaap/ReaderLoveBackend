from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from .base import BaseWithoutId


class BookCollectionAssociation(BaseWithoutId):
    __tablename__ = "book_collection_association"

    collection_id: Mapped[int] = mapped_column(
        ForeignKey("book_collections.id", ondelete="CASCADE"), primary_key=True
    )
    book_id: Mapped[int] = mapped_column(
        ForeignKey("books.id", ondelete="CASCADE"), primary_key=True
    )
