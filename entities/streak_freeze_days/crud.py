from datetime import date

from loguru import logger
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from core.models.streak_freeze_days import StreakFreezeDay, StreakFreezeSource
from .schema import (
    StreakFreezeDayCreate,
    StreakFreezeDayUpdate,
    StreakFreezeDayUpdatePartial,
)


async def get_freeze_day_by_id(
    session: AsyncSession, freeze_day_id: int
) -> StreakFreezeDay | None:
    statement = select(StreakFreezeDay).where(StreakFreezeDay.id == freeze_day_id)
    result = await session.execute(statement)
    return result.scalar_one_or_none()


async def get_freeze_day_by_date(
    session: AsyncSession, user_id: str, frozen_date: date
) -> StreakFreezeDay | None:
    statement = select(StreakFreezeDay).where(
        StreakFreezeDay.user_id == user_id, StreakFreezeDay.frozen_date == frozen_date
    )
    result = await session.execute(statement)
    return result.scalar_one_or_none()


async def get_user_freeze_days(
    session: AsyncSession,
    user_id: str,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[StreakFreezeDay]:
    statement = select(StreakFreezeDay).where(StreakFreezeDay.user_id == user_id)

    if start_date:
        statement = statement.where(StreakFreezeDay.frozen_date >= start_date)
    if end_date:
        statement = statement.where(StreakFreezeDay.frozen_date <= end_date)

    statement = statement.order_by(StreakFreezeDay.frozen_date.desc())
    result = await session.execute(statement)
    return list(result.scalars().all())


async def is_date_frozen(
    session: AsyncSession, user_id: str, target_date: date
) -> bool:
    freeze_day = await get_freeze_day_by_date(session, user_id, target_date)
    return freeze_day is not None


async def create_freeze_day(
    session: AsyncSession, freeze_data: StreakFreezeDayCreate
) -> StreakFreezeDay:
    freeze_day = StreakFreezeDay(**freeze_data.model_dump())

    try:
        session.add(freeze_day)
        await session.commit()
        await session.refresh(freeze_day)
        logger.info(
            f"Created freeze day {freeze_day.frozen_date} "
            f"(source={freeze_day.source}) for user {freeze_day.user_id}"
        )
    except IntegrityError as e:
        await session.rollback()
        logger.warning(
            f"Freeze day {freeze_data.frozen_date} already exists for user {freeze_data.user_id}"
        )
        e.add_note("Freeze day for this date already exists for this user")
        raise

    return freeze_day


async def get_or_create_freeze_day(
    session: AsyncSession,
    user_id: str,
    streak_id: int,
    frozen_date: date,
    source: StreakFreezeSource = StreakFreezeSource.AUTOMATIC,
) -> tuple[StreakFreezeDay, bool]:
    existing = await get_freeze_day_by_date(session, user_id, frozen_date)

    if existing:
        return existing, False

    freeze_day = StreakFreezeDay(
        user_id=user_id, streak_id=streak_id, frozen_date=frozen_date, source=source
    )

    try:
        session.add(freeze_day)
        await session.commit()
        await session.refresh(freeze_day)
        logger.info(
            f"Applied freeze on {frozen_date} ({source.value}) for user {user_id}"
        )
        return freeze_day, True
    except IntegrityError:
        await session.rollback()
        existing_after_race = await get_freeze_day_by_date(
            session, user_id, frozen_date
        )

        if existing_after_race:
            return existing_after_race, False
        raise


async def update_freeze_day(
    session: AsyncSession,
    freeze_day: StreakFreezeDay,
    freeze_update: StreakFreezeDayUpdate | StreakFreezeDayUpdatePartial,
    partial: bool = False,
) -> StreakFreezeDay:
    update_data = freeze_update.model_dump(exclude_unset=partial)

    for key, value in update_data.items():
        setattr(freeze_day, key, value)

    await session.commit()
    await session.refresh(freeze_day)
    logger.info(
        f"Update freeze day {freeze_day.id} ({freeze_day.frozen_date}) for user {freeze_day.user_id}"
    )
    return freeze_day


async def delete_freeze_day(
    session: AsyncSession, user_id: str, frozen_date: date
) -> bool:
    statement = delete(StreakFreezeDay).where(
        StreakFreezeDay.user_id == user_id, StreakFreezeDay.frozen_date == frozen_date
    )
    result = await session.execute(statement)
    await session.commit()

    if result.rowcount > 0:
        logger.info(f"Deleted freeze day by {frozen_date} for user {user_id}")
        return True
    logger.info(f"Freeze day {frozen_date} for user {user_id} not found")
    return False
