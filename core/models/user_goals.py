from typing import TYPE_CHECKING
from enum import Enum
from datetime import datetime
import os

from sqlalchemy import (
    String,
    DateTime,
    Integer,
    Boolean,
    ForeignKey,
    Enum as SqlEnum,
    func,
)

from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .users import User
    from .user_goals_progress import UserGoalsProgress


class UserGoalCategory(str, Enum):
    PAGES_PER_DAY = "Сторінки за день"
    BOOKS_PER_YEAR = "Книги за рік"
    BOOKS_PER_MONTH = "Книги за місяць"
    READING_STREAK = "Читацька серія"


class GoalPeriod(str, Enum):
    DAILY = "daily"
    MONTHLY = "monthly"
    YEARLY = "yearly"
    INFINITE = "infinite"


class UserGoals(Base):
    __tablename__ = "user_goals"

    user_id: Mapped[str] = mapped_column(
        String(int(os.getenv("NANOID_KEY_SIZE"))),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    target_value: Mapped[int] = mapped_column(Integer, nullable=False)

    category: Mapped[UserGoalCategory] = mapped_column(
        SqlEnum(UserGoalCategory, values_callable=lambda enum: [e.value for e in enum]),
        default=UserGoalCategory.READING_STREAK,
        server_default=UserGoalCategory.READING_STREAK.value,
        nullable=False,
    )
    period: Mapped[GoalPeriod] = mapped_column(
        SqlEnum(GoalPeriod, values_callable=lambda enum: [e.value for e in enum]),
        default=GoalPeriod.INFINITE,
        server_default=GoalPeriod.INFINITE.value,
        nullable=False,
    )

    deadline: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    is_completed: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="0"
    )
    icon: Mapped[str] = mapped_column(String(255), nullable=True, default=None)

    user: Mapped["User"] = relationship("User", back_populates="goals")
    progress_log: Mapped[list["UserGoalsProgress"]] = relationship(
        "UserGoalsProgress", back_populates="goal", cascade="all, delete-orphan"
    )

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(target_value={self.target_value}, category={self.category.value})"
