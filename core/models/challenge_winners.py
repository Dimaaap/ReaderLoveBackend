from typing import TYPE_CHECKING
from datetime import datetime
import os

from sqlalchemy import ForeignKey, String, Integer, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, BaseWithoutId

if TYPE_CHECKING:
    from .users import User
    from .challenge import Challenge


class ChallengeWinner(BaseWithoutId):
    __tablename__ = "challenge_winners"

    challenge_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("challenges.id", ondelete="CASCADE"), primary_key=True
    )

    user_id: Mapped[str] = mapped_column(
        String(int(os.getenv("NANOID_KEY_SIZE"))),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(user_id={self.user_id}, created_at={self.created_at})"


class ChallengeSuperWinner(BaseWithoutId):
    __tablename__ = "challenge_super_winners"

    challenge_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("challenges.id", ondelete="CASCADE"), primary_key=True
    )

    user_id: Mapped[str] = mapped_column(
        String(int(os.getenv("NANOID_KEY_SIZE"))),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(challenge_id={self.challenge_id}, user_id={self.user_id})"
