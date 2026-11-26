from datetime import datetime
import os
from typing import TYPE_CHECKING

from sqlalchemy import (
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .reading_streak_state import ReadingStreak


class StreakMilestone(Base):
    __tablename__ = "streak_milestones"

    __table_args__ = (
        UniqueConstraint(
            "user_id", "milestone_days", name="uq_streak_milestone_user_days"
        ),
    )

    user_id: Mapped[str] = mapped_column(
        String(int(os.getenv("NANOID_KEY_SIZE", 21))),
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

    milestone_days: Mapped[int] = mapped_column(Integer, nullable=False)

    is_celebrated: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="0", nullable=False
    )

    shared_in_app: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="0", nullable=False
    )

    reached_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    celebrated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    streak: Mapped["ReadingStreak"] = relationship(
        "ReadingStreak", back_populates="milestones"
    )

    def __str__(self) -> str:
        return (
            f"{self.__class__.__name__}"
            f"(user_id={self.user_id}, days={self.milestone_days})"
        )
