from typing import TYPE_CHECKING

from datetime import date, datetime
from typing import Optional
from enum import Enum as PyEnum

from sqlalchemy import (
    String,
    Text,
    Integer,
    Date,
    Boolean,
    DateTime,
    ForeignKey,
    Enum,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.models.base import Base

if TYPE_CHECKING:
    from .user_challenge import UserChallenge
    from .challenge_book import ChallengeBook


class ChallengeType(str, PyEnum):
    BOOK = "book"
    COMIC = "comic"
    MANGA = "manga"
    PAGES = "pages"


class Challenge(Base):
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    slug: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )

    target_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    challenge_type: Mapped[ChallengeType] = mapped_column(
        Enum(
            ChallengeType,
            values_callable=lambda enum: [e.value for e in enum],
            name="challengetype",
        ),
        default=ChallengeType.BOOK,
        server_default=ChallengeType.BOOK.value,
        nullable=False,
    )

    active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="1", nullable=True
    )

    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)

    badge_color: Mapped[Optional[str]] = mapped_column(
        String(30), nullable=True, default="#3B82F6"
    )
    sponsor_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    publisher_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("book_publishers.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    participants: Mapped[list["UserChallenge"]] = relationship(
        "UserChallenge",
        back_populates="challenge",
        cascade="all, delete-orphan",
    )

    challenge_books: Mapped[list["ChallengeBook"]] = relationship(
        "ChallengeBook", back_populates="challenge", cascade="all, delete-orphan"
    )

    def __str__(self):
        return f"{self.__class__.__name__}(title={self.title}, slug={self.slug} badge color={self.badge_color})"
