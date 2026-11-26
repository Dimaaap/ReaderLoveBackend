from datetime import datetime, date
from enum import Enum
import os
from typing import TYPE_CHECKING

from sqlalchemy import (
    String,
    DateTime,
    Date,
    Integer,
    ForeignKey,
    Enum as SqlEnum,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .users import User
    from .streak_freeze_days import StreakFreezeDay
    from .streak_milestone import StreakMilestone


class StreakGoalType(str, Enum):
    MINUTES = "minutes"
    PAGES = "pages"


class StreakFreezeSource(str, Enum):
    AUTOMATIC = "automatic"
    MANUAL = "manual"
    REWARD = "reward"


class ReadingStreak(Base):
    __tablename__ = "reading_streaks"

    user_id: Mapped[str] = mapped_column(
        String(int(os.getenv("NANOID_KEY_SIZE", 21))),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    current_streak: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    best_streak: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    last_active_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    freezes_available: Mapped[int] = mapped_column(
        Integer, default=1, server_default="1", nullable=False
    )
    max_freezes: Mapped[int] = mapped_column(
        Integer, default=2, server_default="2", nullable=False
    )

    goal_type: Mapped[StreakGoalType] = mapped_column(
        SqlEnum(
            StreakGoalType,
            values_callable=lambda enum: [e.value for e in enum],
            name="streakgoaltype",
        ),
        default=StreakGoalType.MINUTES,
        server_default=StreakGoalType.MINUTES.value,
        nullable=False,
    )

    daily_goal_value: Mapped[int] = mapped_column(
        Integer, default=15, server_default="15", nullable=False
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user: Mapped["User"] = relationship("User", back_populates="reading_streak")
    freezes: Mapped[list["StreakFreezeDay"]] = relationship(
        "StreakFreezeDay", back_populates="streak", cascade="all, delete-orphan"
    )
    milestones: Mapped[list["StreakMilestone"]] = relationship(
        "StreakMilestone", back_populates="streak", cascade="all, delete-orphan"
    )

    def __str__(self) -> str:
        return (
            f"{self.__class__.__name__}"
            f"(user_id={self.user_id}, current_streak={self.current_streak}, best_streak={self.best_streak})"
        )
