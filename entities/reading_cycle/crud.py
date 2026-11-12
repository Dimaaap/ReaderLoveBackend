from datetime import datetime, timezone

from fastapi import HTTPException, status
from loguru import logger

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.models import ReadingCycle, User, UserBookAssociation, Book
from core.models.reading_cycle import ReadingCycleStatus
from core.models.user_book_association import BookReadStatus, TrackingType


async def get_user_id_by_username(
    session: AsyncSession,
    username: str,
) -> str:
    result = await session.execute(select(User.id).where(User.username == username))

    user_id = result.scalar_one_or_none()

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return user_id


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
    session: AsyncSession, username: str, cycle_id: int
) -> ReadingCycle | None:
    logger.info(f"Try to get reading cycle with id {cycle_id}")

    user_id = await get_user_id_by_username(session, username)

    result = await session.execute(
        select(ReadingCycle).where(
            ReadingCycle.id == cycle_id,
            ReadingCycle.user_id == user_id,
        )
    )

    return result.scalar_one_or_none()


async def get_active_reading_cycle(
    session: AsyncSession, username: str, book_id: int
) -> ReadingCycle | None:
    logger.info(
        f"Try to get active reading cycle for user {username} and book {book_id}"
    )

    user_id = await get_user_id_by_username(session, username)

    statement = select(ReadingCycle).where(
        ReadingCycle.user_id == user_id,
        ReadingCycle.book_id == book_id,
        ReadingCycle.status == ReadingCycleStatus.IN_PROGRESS,
    )

    result = await session.execute(statement)
    return result.scalar_one_or_none()


async def get_user_reading_cycles(
    username: str, session: AsyncSession
) -> list[ReadingCycle]:
    logger.info(f"Try to get all reading cycles for user {username}")

    statement = (
        select(ReadingCycle)
        .join(ReadingCycle.user_book)
        .join(UserBookAssociation.user)
        .where(User.username == username)
        .order_by(ReadingCycle.started_at.desc(), ReadingCycle.read_number.desc())
    )

    result = await session.execute(statement)
    return list(result.scalars().unique().all())


async def get_book_reading_cycles(
    username: str, book_id: int, session: AsyncSession
) -> list[ReadingCycle]:
    logger.info(f"Try to get reading cycles for user {username}, book {book_id}")

    statement = (
        select(ReadingCycle)
        .join(ReadingCycle.user_book)
        .join(UserBookAssociation.user)
        .where(
            User.username == username,
            ReadingCycle.book_id == book_id,
        )
        .order_by(ReadingCycle.read_number.desc())
    )

    result = await session.execute(statement)
    return list(result.scalars().unique().all())


async def create_reading_cycle(
    session: AsyncSession, username: str, book_id: int
) -> ReadingCycle:
    logger.info(f"Try to create reading cycle for user {username}, book {book_id}")

    user_result = await session.execute(select(User).where(User.username == username))
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    book_result = await session.execute(select(Book).where(Book.id == book_id))
    book = book_result.scalar_one_or_none()

    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Book not found"
        )

    association = await get_user_book_association(session, username, book_id, lock=True)

    if not association:
        association = UserBookAssociation(
            user_id=user.id, book_id=book_id, status=BookReadStatus.READING
        )
        session.add(association)
        await session.flush()

    active_cycle = await get_active_reading_cycle(session, username, book_id)

    if active_cycle:
        return active_cycle

    max_number_result = await session.execute(
        select(func.max(ReadingCycle.read_number)).where(
            ReadingCycle.user_id == user.id, ReadingCycle.book_id == book_id
        )
    )

    max_read_number = max_number_result.scalar_one_or_none() or 0

    cycle = ReadingCycle(
        user_id=user.id,
        book_id=book_id,
        read_number=max_read_number + 1,
        status=ReadingCycleStatus.IN_PROGRESS,
    )

    association.status = BookReadStatus.READING
    session.add(cycle)
    await session.commit()
    await session.refresh(cycle)

    logger.info(f"Created reading cycle {cycle.id}")

    return cycle


async def reread_book(
    session: AsyncSession, username: str, book_id: int
) -> ReadingCycle:
    logger.info(f"Try to create rereading cycle for user {username} and book {book_id}")

    user_result = await session.execute(select(User).where(User.username == username))
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    association = await get_user_book_association(
        session, user_id=user.id, book_id=book_id, lock=True
    )

    if not association:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book is not found in user`s library",
        )

    active_cycle = await get_active_reading_cycle(session, username, book_id)

    if active_cycle:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="There is already an active reading cycle",
        )

    last_cycle_result = await session.execute(
        select(ReadingCycle)
        .where(ReadingCycle.user_id == user.id, ReadingCycle.book_id == book_id)
        .order_by(ReadingCycle.read_number.desc())
        .limit(1)
        .with_for_update()
    )

    last_cycle = last_cycle_result.scalar_one_or_none()

    if not last_cycle:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="There is no previous reading cycles",
        )

    if last_cycle.status != ReadingCycleStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Previous reading cycle is not completed",
        )

    new_cycle = ReadingCycle(
        user_id=user.id,
        book_id=book_id,
        read_number=last_cycle.read_number + 1,
        status=ReadingCycleStatus.IN_PROGRESS,
        last_read_page=0,
        last_read_percent=0.0,
    )

    association.status = BookReadStatus.READING
    association.last_read_page = 0
    association.last_read_percent = 0.0

    session.add(new_cycle)

    logger.info(f"Created rereading cycle {new_cycle.id}")

    return new_cycle


async def update_reading_cycle_progress(
    session: AsyncSession,
    cycle: ReadingCycle,
    page: int | None = None,
    percent: float | None = None,
) -> ReadingCycle:
    if cycle.status == ReadingCycleStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update a completed reading cycle",
        )

    association = await get_user_book_association(session, cycle.user_id, cycle.book_id)

    if not association:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User book association not found",
        )

    pages_count = association.book.pages_count

    if association.tracking_type == TrackingType.PAGES:
        if page is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Page is required for page tracking",
            )

        if page < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Page cannot be negative",
            )

        if pages_count and page > pages_count:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Page exceeds the total number of pages",
            )

        cycle.last_read_page = page
        cycle.last_read_percent = (
            round(page / pages_count * 100, 2) if pages_count else 0.0
        )
    elif association.tracking_type == TrackingType.PERCENT:
        if percent is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Percent is required for percent tracking",
            )

        if not 0 <= percent <= 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Percent must be between 0 and 100",
            )

        cycle.last_read_percent = percent

        if pages_count:
            cycle.last_read_page = round(pages_count * percent / 100)

    association.last_read_page = cycle.last_read_page
    association.last_read_percent = cycle.last_read_percent

    if cycle.last_read_percent >= 100:
        cycle.status = ReadingCycleStatus.COMPLETED
        cycle.finished_at = datetime.now(timezone.utc)
        association.status = BookReadStatus.FINISHED

    await session.commit()
    await session.refresh(cycle)

    logger.info(
        f"Updated reading cycle {cycle.id}: {cycle.last_read_percent}%, {cycle.last_read_page} pages"
    )

    return cycle


async def complete_reading_cycle(
    session: AsyncSession, cycle: ReadingCycle
) -> ReadingCycle:
    if cycle.status == ReadingCycleStatus.COMPLETED:
        return cycle

    association = await get_user_book_association(session, cycle.user_id, cycle.book_id)

    if not association:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User book association not found",
        )

    pages_count = association.book.pages_count

    cycle.status = ReadingCycleStatus.COMPLETED
    cycle.finished_at = datetime.now(timezone.utc)
    cycle.last_read_percent = 100.0

    if pages_count:
        cycle.last_read_page = pages_count

    association.status = BookReadStatus.FINISHED
    association.last_read_page = cycle.last_read_page
    association.last_read_percent = 100.0

    await session.commit()
    await session.refresh(cycle)

    logger.info(f"Completed reading cycle {cycle.id}")

    return cycle


async def delete_reading_cycle(session: AsyncSession, cycle: ReadingCycle) -> None:
    logger.info(f"Try to delete reading cycle {cycle.id}")

    association = await get_user_book_association(
        session=session, user_id=cycle.user_id, book_id=cycle.book_id
    )

    if not association:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User book association not found",
        )

    if cycle.status == ReadingCycleStatus.IN_PROGRESS:
        previous_cycle_result = await session.execute(
            select(ReadingCycle)
            .where(
                ReadingCycle.user_id == cycle.user_id,
                ReadingCycle.book_id == cycle.book_id,
                ReadingCycle.id != cycle.id,
                ReadingCycle.status == ReadingCycleStatus.COMPLETED,
            )
            .order_by(ReadingCycle.read_number.desc())
            .limit(1)
        )

        previous_cycle = previous_cycle_result.scalar_one_or_none()

        if previous_cycle:
            association.status = BookReadStatus.FINISHED
            association.last_read_page = previous_cycle.last_read_page
            association.last_read_percent = previous_cycle.last_read_percent
        else:
            association.status = BookReadStatus.WANT_TO_READ
            association.last_read_page = 0
            association.last_read_percent = 0

    await session.delete(cycle)

    logger.info(f"Deleted reading cycle {cycle.id}")
