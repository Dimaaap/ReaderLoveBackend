from typing import TYPE_CHECKING

from datetime import datetime
from typing import Optional
from enum import Enum as PyEnum

from sqlalchemy import String, Integer, DateTime, ForeignKey, Enum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.models.base import Base

if TYPE_CHECKING:
    from .users import User
    from .challenge import Challenge


class UserChallengeStatus(str, PyEnum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class UserChallenge(Base):
    __tablename__ = "user_challenges"

    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    challenge_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("challenges.id", ondelete="CASCADE"), primary_key=True
    )

    current_progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    status: Mapped[UserChallengeStatus] = mapped_column(
        Enum(
            UserChallengeStatus,
            values_callable=lambda enum: [e.value for e in enum],
            name="userchallengestatus",
        ),
        default=UserChallengeStatus.IN_PROGRESS,
        server_default=UserChallengeStatus.IN_PROGRESS.value,
        nullable=False,
    )

    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )

    user: Mapped["User"] = relationship("User", back_populates="challenges")
    challenge: Mapped["Challenge"] = relationship(
        "Challenge", back_populates="participants"
    )

    def __str__(self) -> str:
        return f"{self.__class__.__name__}({self.__class__.__name__}(status={self.status}))"
