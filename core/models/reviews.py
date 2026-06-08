from .base import Base

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column


class Review(Base):
    review_text: Mapped[str] = mapped_column(Text, nullable=False)
    user_name: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)

    def __str__(self):
        return f"{ self.__class__.__name__ }(user_name={ self.user_name }, title={self.title})"
