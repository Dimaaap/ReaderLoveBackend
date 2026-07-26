import os
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Boolean, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .users import User


class UserSettings(Base):
    __tablename__ = "user_settings"

    user_id: Mapped[str] = mapped_column(
        String(int(os.getenv("NANOID_KEY_SIZE"))),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )

    email_notifications: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=true()
    )

    reading_reminders: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=true()
    )

    book_recommendations: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=true()
    )

    is_public_profile: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=true()
    )

    is_show_reading_progress: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=true()
    )

    allow_friends_recommendations: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=true()
    )

    show_statistics: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=true()
    )

    show_bookshelf: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=true()
    )

    show_favorite_books: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=true()
    )

    show_notes: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=true()
    )

    show_quotes: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=true()
    )

    show_goals: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=true()
    )

    show_current_book: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=true()
    )

    show_followers: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=true()
    )

    allow_private_messages: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=true()
    )

    show_online_status: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=true()
    )

    show_last_seen: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=true()
    )

    user: Mapped["User"] = relationship("User", back_populates="settings")

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(user_id={self.user_id})"
