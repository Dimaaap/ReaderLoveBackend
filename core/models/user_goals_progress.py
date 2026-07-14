from typing import TYPE_CHECKING
from datetime import date

from sqlalchemy import Integer, Date, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .user_goals import UserGoals


class UserGoalsProgress(Base):
    __tablename__ = "user_goals_progress"

    goal_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("user_goals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    value: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )

    log_date: Mapped[date] = mapped_column(
        Date,
        server_default=func.current_date(),
        default=date.today(),
        nullable=False,
        index=True,
    )
    goal: Mapped["UserGoals"] = relationship("UserGoals", back_populates="progress_log")

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(value={self.value}, date={self.log_date})"
