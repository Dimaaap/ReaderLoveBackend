from datetime import datetime
from enum import Enum
import os
from typing import TYPE_CHECKING

from utils.generate_nano import generate_nanoid
from .base import Base

from sqlalchemy import String, DateTime, Boolean, Enum as SqlEnum, func, false
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from .books import Book
    from .reading_sessions import ReadingSession


class UserRole(str, Enum):
    USER = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"


class RegisterWays(str, Enum):
    SITE = "site"
    GOOGLE = "google"
    GITHUB = "github"


class User(Base):
    id: Mapped[str] = mapped_column(
        String(int(os.getenv("NANOID_KEY_SIZE"))),
        primary_key=True,
        default=generate_nanoid,
    )

    username: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=True)

    date_joined: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    role: Mapped[UserRole] = mapped_column(
        SqlEnum(UserRole, values_callable=lambda enum: [e.value for e in enum]),
        default=UserRole.USER,
        server_default=UserRole.USER.value,
        nullable=False,
    )

    is_verified: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false(), nullable=False
    )

    register_way: Mapped[RegisterWays] = mapped_column(
        SqlEnum(RegisterWays, values_callable=lambda enum: [e.value for e in enum]),
        default=RegisterWays.SITE,
        server_default=RegisterWays.SITE.value,
        nullable=False,
    )

    books: Mapped[list["Book"]] = relationship(
        secondary="user_book_association", back_populates="users"
    )

    reading_sessions: Mapped[list["ReadingSession"]] = relationship(
        "ReadingSession", back_populates="user", cascade="all, delete-orphan"
    )

    def __str__(self) -> str:
        return (
            f"{self.__class__.__name__}(username={self.username}, email={self.email})"
        )
