from datetime import datetime, timezone

from loguru import logger
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from core.models.streak_milestone import StreakMilestone
from entities.reading_streak_milestones.schema import (
    StreakMilestoneCreate,
    StreakMilestoneUpdate,
    StreakMilestoneSchema,
)


async def get_milestone_by_id(
    session: AsyncSession, milestone_id: int
) -> StreakMilestone | None:
    statement = select(StreakMilestone).where(StreakMilestone.id == milestone_id)
    result = await session.execute(statement)

    return result.scalar_one_or_none()


async def get_user_milestones(
    session: AsyncSession, user_id: str, only_uncelebrated: bool = False
) -> list[StreakMilestone]:
    statement = (
        select(StreakMilestone)
        .where(StreakMilestone.user_id == user_id)
        .order_by(StreakMilestone.milestone_days.asc())
    )

    if only_uncelebrated:
        statement = statement.where(StreakMilestone.is_celebrated.is_(False))

    result = await session.execute(statement)
    return list(result.scalars().all())


async def get_user_milestone_by_days(
    session: AsyncSession, user_id: str, milestone_days: int
) -> StreakMilestone | None:
    statement = select(StreakMilestone).where(
        StreakMilestone.user_id == user_id,
        StreakMilestone.milestone_days == milestone_days,
    )

    result = await session.execute(statement)
    return result.scalar_one_or_none()


async def create_milestone(
    session: AsyncSession, milestone_data: StreakMilestoneCreate
) -> StreakMilestone:
    milestone = StreakMilestone(**milestone_data.model_dump())

    try:
        session.add(milestone)
        await session.commit()
        await session.refresh(milestone)
        logger.info(
            f"Created milestone {milestone.milestone_days}d for user {milestone.user_id}"
        )
    except IntegrityError as e:
        await session.rollback()
        logger.warning(
            f"Milestone {milestone_data.milestone_days}d already exists for user {milestone.user_id}"
        )
        e.add_note("Milestone with this number of days already exists for this user")
        raise

    return milestone


async def get_or_create_milestone(
    session: AsyncSession, user_id: str, streak_id: int, milestone_days: int
) -> tuple[StreakMilestone, bool]:
    existing = await get_user_milestone_by_days(session, user_id, milestone_days)

    if existing:
        return existing, False

    milestone = StreakMilestone(
        user_id=user_id,
        streak_id=streak_id,
        milestone_days=milestone_days,
        is_celebrated=False,
        shared_in_app=False,
    )

    try:
        session.add(milestone)
        await session.commit()
        await session.refresh(milestone)
        logger.info(f"Unlocked milestone {milestone_days}d for user {user_id} ")
        return milestone, True
    except IntegrityError as e:
        await session.rollback()
        existing_after_race = await get_user_milestone_by_days(
            session, user_id, milestone_days
        )

        if existing_after_race:
            return existing_after_race, False
        raise


async def update_milestone(
    session: AsyncSession,
    milestone: StreakMilestone,
    milestone_update: StreakMilestoneUpdate | StreakMilestoneUpdatePartial,
    partial: bool = False,
) -> StreakMilestone:
    update_data = milestone_update.model_dump(exclude_unset=partial)

    for key, value in update_data.items():
        setattr(milestone, key, value)

    await session.commit()
    await session.refresh(milestone)
    logger.info(f"Updated milestone {milestone.id} for user {milestone.user_id}")
    return milestone


async def celebrate_milestone(
    session: AsyncSession, user_id: str, milestone_days: int, share_in_app: bool = False
) -> StreakMilestoneSchema | None:
    milestone = await get_user_milestone_by_days(session, user_id, milestone_days)

    if not milestone:
        logger.warning(f"Milestone: {milestone_days}d not found for user {user_id}")
        return None

    milestone.is_celebrated = True
    if share_in_app:
        milestone.shared_in_app = True
    if milestone.celebrated_at is None:
        milestone.celebrated_at = datetime.now(timezone.utc)

    await session.commit()
    await session.refresh(milestone)
    logger.info(
        f"Celebrated milestone {milestone_days}d for user {user_id} (shared_in_app={milestone.shared_in_app}"
    )

    return StreakMilestoneSchema.model_validate(milestone)


async def delete_milestone(
    session: AsyncSession, user_id: str, milestone_days: int
) -> bool:
    statement = delete(StreakMilestone).where(
        StreakMilestone.user_id == user_id,
        StreakMilestone.milestone_days == milestone_days,
    )
    result = await session.execute(statement)
    await session.commit()

    if result.rowcount > 0:
        logger.info(f"Deleted milestone {milestone_days}d for user {user_id}")
        return True

    logger.info(f"Milestone {milestone_days}d for user {user_id} not found")
    return False
