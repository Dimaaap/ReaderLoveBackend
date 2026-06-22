from .base import Base

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column


class Book(Base):
    title: Mapped[str] = mapped_column(String(255), nullable=False)
