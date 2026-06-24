from .base import Base

from sqlalchemy import String, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column


class Book(Base):
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    image_link: Mapped[str] = mapped_column(String(255), nullable=True)
    pages_count: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[Text] = mapped_column(Text, nullable=True)
    publish_date: Mapped[str] = mapped_column(String(100), nullable=True)
    language: Mapped[str] = mapped_column(String(50), nullable=True)

    def __str__(self):
        return f"{self.__class__.__name__}(title={self.title}, slug={self.slug})"
