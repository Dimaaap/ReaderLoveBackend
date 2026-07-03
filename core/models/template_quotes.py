from datetime import date

from .base import Base

from sqlalchemy import String, Text, Date
from sqlalchemy.orm import Mapped, mapped_column


class TemplateQuote(Base):
    __tablename__ = "template_quotes"

    quote: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    author: Mapped[str] = mapped_column(String(255), nullable=False)
    last_shown_at: Mapped[date | None] = mapped_column(
        Date, nullable=True, default=None
    )

    def __str__(self):
        return f"{self.__class__.__name__}(quote={ self.quote[:20] })"
