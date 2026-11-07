from datetime import datetime, timezone

from fastapi import HTTPException, status
from loguru import logger

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.models import ReadingCycle, ReadingSession, User, UserBookAssociation, Book
from core.models.reading_cycle import ReadingCycleStatus
from core.models.user_book_association import BookReadStatus, TrackingType


async def get_user_book_association(
    session: AsyncSession, user_id: str, book_id: int, lock: bool = False
) -> UserBookAssociation | None:
    statement = (
        select(UserBookAssociation)
        .where(
            UserBookAssociation.user_id == user_id,
            UserBookAssociation.book_id == book_id,
        )
        .options(selectinload(UserBookAssociation.book))
    )
