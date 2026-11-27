from datetime import date

from loguru import logger
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from core.models.reading_streak_state import ReadingStreak
from .schema import (
    ReadingStreakCreate,
    ReadingStreakUpdate,
    ReadingStreakUpdatePartial,
    ReadingStreakGoalUpdate,
)


async def get_streak_by_id(
    session: AsyncSession, streak_id: int
) -> ReadingStreak | None:
    statement = select(ReadingStreak).where(ReadingStreak.id == streak_id)
    result = await session.execute(statement)
    return result.scalar_one_or_none()


async def get_streak_by_user_id(
    session: AsyncSession, user_id: str, with_relations: bool = False
) -> ReadingStreak | None:
    statement = select(ReadingStreak).where(ReadingStreak.user_id == user_id)

    if with_relations:
        statement = statement.options(
            selectinload(ReadingStreak.freezes), selectinload(ReadingStreak.milestones)
        )
    result = await session.execute(statement)
    return result.scalar_one_or_none()


async def create_streak(
    session: AsyncSession, streak_data: ReadingStreakCreate
) -> ReadingStreak:
    streak = ReadingStreak(**streak_data.model_dump())

    try:
        session.add(streak)
        await session.commit()
        await session.refresh(streak)
        logger.info(f"Created reading streak for user {streak.user_id}")
    except IntegrityError as e:
        await session.rollback()
        logger.warning(f"Reading streak already exists for user {streak_data.user_id}")
        e.add_note("Reading streak for this user already exists")
        raise
    return streak


async def get_or_create_streak(
    session: AsyncSession, user_id: str, with_relations: bool = False
) -> tuple[ReadingStreak, bool]:
    existing = await get_streak_by_user_id(session, user_id, with_relations)

    if existing:
        return existing, False

    streak = ReadingStreak(user_id=user_id)

    try:
        session.add(streak)
        await session.commit()
        await session.refresh(streak)
        logger.info(f"Initialized reading streak for user {user_id}")

        if with_relations:
            reloaded = await get_streak_by_user_id(
                session, user_id, with_relations=True
            )
            return reloaded or streak, True
        return streak, True
    except IntegrityError:
        await session.rollback()
        existing_after_race = await get_streak_by_user_id(
            session, user_id, with_relations=with_relations
        )

        if existing_after_race:
            return existing_after_race, False
        raise


async def update_streak(
    session: AsyncSession,
    streak: ReadingStreak,
    streak_update: ReadingStreakUpdate | ReadingStreakUpdatePartial,
    partial: bool = False,
) -> ReadingStreak:
    update_data = streak_update.model_dump(exclude_unset=partial)

    for key, value in update_data.items():
        setattr(streak, key, value)

    await session.commit()
    await session.refresh(streak)

    logger.info(
        f"Updated reading streak for user {streak.user_id}(current={streak.current_streak}, best={streak.best_streak})"
    )

    return streak


async def update_streak_goal(
    session: AsyncSession, streak: ReadingStreak, goal_update: ReadingStreakGoalUpdate
) -> ReadingStreak:
    update_data = goal_update.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(streak, key, value)

    await session.commit()
    await session.refresh(streak)
    logger.info(
        f"Updated streak goal for user {streak.user_id}: {streak.daily_goal_value} {streak.goal_type.value}"
    )
    return streak


async def add_streak_freezes(
    session: AsyncSession, streak: ReadingStreak, amount: int = 1
) -> ReadingStreak:
    if amount <= 0:
        return streak

    streak.freezes_available = min(
        streak.max_freezes, streak.freezes_available + amount
    )
    await session.commit()
    await session.refresh(streak)
    logger.info(
        f"Added {amount} freeze(s) for user {streak.user_id}(available={streak.freezes_available}/{streak.max_freezes})"
    )
    return streak


async def consume_streak_freeze(session: AsyncSession, streak: ReadingStreak) -> bool:
    if streak.freezes_available <= 0:
        return False

    streak.freezes_available -= 1
    await session.commit()
    await session.refresh(streak)
    logger.info(
        f"Consumed 1 freeze for user {streak.user_id}(remaining={streak.freezes_available}/{streak.max_freezes})"
    )

    return True


async def reset_current_streak(
    session: AsyncSession, streak: ReadingStreak
) -> ReadingStreak:
    streak.current_streak = 0
    await session.commit()
    await session.refresh(streak)
    logger.info(f"Reset current streak to 0 for user {streak.user_id}")
    return streak


async def get_active_streaks_for_check(
    session: AsyncSession, cutoff_date: date
) -> list[ReadingStreak]:
    statement = select(ReadingStreak).where(
        ReadingStreak.current_streak > 0,
        ReadingStreak.last_active_date.is_not(None),
        ReadingStreak.last_active_date < cutoff_date,
    )

    result = await session.execute(statement)
    return list(result.scalars().all())


async def delete_streak(session: AsyncSession, user_id: str) -> bool:
    statement = delete(ReadingStreak).where(ReadingStreak.user_id == user_id)
    result = await session.execute(statement)
    await session.commit()

    if result.rowcount > 0:
        logger.info(f"Deleted reading streak for user {user_id}")
        return True

    logger.info(f"Reading streak for user {user_id} not found")
    return False
