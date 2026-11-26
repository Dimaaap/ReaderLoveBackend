from datetime import date, datetime
import os

from typing import TYPE_CHECKING
from sqlalchemy import (
    String,
    Integer,
    UniqueConstraint,
    ForeignKey,
    Date,
    DateTime,
    Enum as SqlEnum,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .reading_streak_state import StreakFreezeSource

if TYPE_CHECKING:
    from .reading_streak_state import ReadingStreak


class StreakFreezeDay(Base):
    __tablename__ = "streak_freeze_days"

    __table_args__ = (
        UniqueConstraint("user_id", "frozen_date", name="uq_streak_freeze_user_date"),
    )

    user_id: Mapped[str] = mapped_column(
        String(int(os.getenv("NANOID_KEY_SIZE"))),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    streak_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("reading_streaks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    frozen_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    source: Mapped[StreakFreezeSource] = mapped_column(
        SqlEnum(
            StreakFreezeSource,
            values_callable=lambda enum: [e.value for e in enum],
            name="streakfreezesource",
        ),
        default=StreakFreezeSource.AUTOMATIC,
        server_default=StreakFreezeSource.AUTOMATIC.value,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    streak: Mapped["ReadingStreak"] = relationship(
        "ReadingStreak", back_populates="freezes"
    )

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(user_id={self.user_id}, frozen_date={self.frozen_date})"
