from datetime import datetime

from .base import Base

from sqlalchemy import Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column


class Oferta(Base):
    __tablename__ = "oferta"

    html_code: Mapped[str] = mapped_column(Text, nullable=False)

    last_update: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    def __str__(self):
        return f"{self.__class__.__name__}(html_code={self.html_code})"
