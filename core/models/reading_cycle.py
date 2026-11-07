from datetime import datetime
import os
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    Integer,
    String,
    Float,
    DateTime,
    Enum as SqlEnum,
    func,
    UniqueConstraint,
    ForeignKeyConstraint,
    Index,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .user_book_association import UserBookAssociation
    from .reading_sessions import ReadingSession


class ReadingCycleStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class ReadingCycle(Base):
    __tablename__ = "reading_cycles"

    user_id: Mapped[str] = mapped_column(
        String(int(os.getenv("NANOID_KEY_SIZE"))),
        nullable=False,
    )

    book_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    read_number: Mapped[int] = mapped_column(Integer, nullable=False)

    status: Mapped[ReadingCycleStatus] = mapped_column(
        SqlEnum(
            ReadingCycleStatus,
            values_callable=lambda enum: [e.value for e in enum],
        ),
        default=ReadingCycleStatus.IN_PROGRESS,
        nullable=False,
    )

    last_read_page: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )

    last_read_percent: Mapped[float] = mapped_column(
        Float, default=0.0, server_default="0.0", nullable=False
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["user_id", "book_id"],
            [
                "user_book_association.user_id",
                "user_book_association.book_id",
            ],
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "user_id",
            "book_id",
            "read_number",
            name="uq_reading_cycle_number",
        ),
        Index(
            "uq_active_reading_cycle",
            "user_id",
            "book_id",
            unique=True,
            postgresql_where=text("status = 'in_progress'"),
        ),
    )

    user_book: Mapped["UserBookAssociation"] = relationship(
        "UserBookAssociation",
        back_populates="reading_cycles",
    )

    sessions: Mapped[list["ReadingSession"]] = relationship(
        "ReadingSession",
        back_populates="reading_cycle",
    )

    def __str__(self):
        return (
            f"{self.__class__.__name__}"
            f"(read_number={self.read_number}, status={self.status})"
        )
