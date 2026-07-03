from datetime import datetime
from enum import Enum
import os

from sqlalchemy import ForeignKey, String, DateTime, Enum as SqlEnum, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import BaseWithoutId


class BookReadStatus(str, Enum):
    WANT_TO_READ = "want_to_read"
    READING = "reading"
    FINISHED = "finished"
    PAUSED = "paused"
    ABANDONED = "abandoned"


class UserBookAssociation(BaseWithoutId):
    __tablename__ = "user_book_association"

    user_id: Mapped[int] = mapped_column(
        String(int(os.getenv("NANOID_KEY_SIZE"))),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )

    book_id: Mapped[int] = mapped_column(
        ForeignKey("books.id", ondelete="CASCADE"), primary_key=True
    )

    status: Mapped[BookReadStatus] = mapped_column(
        SqlEnum(BookReadStatus, values_callable=lambda enum: [e.value for e in enum]),
        default=BookReadStatus.WANT_TO_READ,
        server_default=BookReadStatus.WANT_TO_READ.value,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __str__(self):
        return f"{self.__class__.__name__}(user_id={self.user_id}, book_id={self.book_id}, status={self.status})"
