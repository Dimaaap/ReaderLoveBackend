from .base import Base

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column


class SocialLinks(Base):
    __tablename__ = "social_links"

    title: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    link: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    background_color: Mapped[str] = mapped_column(String(7), nullable=True)
    image_src: Mapped[str] = mapped_column(String(50), nullable=True)

    def __str__(self):
        return f"{ self.__class__.__name__ }(title={ self.title }, link={ self.link })"
