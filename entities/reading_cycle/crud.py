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

    if lock:
        statement = statement.with_for_update()
    result = await session.execute(statement)
    return result.scalar_one_or_none()


async def get_reading_cycle_by_id(
    session: AsyncSession, cycle_id: int
) -> ReadingCycle | None:
    logger.info(f"Try to get reading cycle with id {cycle_id}")

    statement = (
        select(ReadingCycle)
        .where(ReadingCycle.id == cycle_id)
        .options(
            selectinload(ReadingCycle.user_book), selectinload(ReadingCycle.sessions)
        )
    )

    result = await session.execute(statement)
    return result.scalar_one_or_none()


async def get_active_reading_cycle(
    session: AsyncSession, username: str, book_id: int
) -> ReadingCycle | None:
    logger.info(
        f"Try to get active reading cycle for user {username} and book {book_id}"
    )

    statement = select(ReadingCycle).where(
        ReadingCycle.user_id == user_id,
    )
