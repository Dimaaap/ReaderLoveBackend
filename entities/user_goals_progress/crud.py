from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from core.models import UserGoalsProgress
from entities.user_goals_progress.schema import (
    UserGoalProgresSchema,
    UserGoalProgressCreate,
    UserGoalProgressUpdate,
    UserGoalProgressUpdatePartial,
)


async def get_all_goal_progresses(session: AsyncSession) -> list[UserGoalProgresSchema]:
    statement = (
        select(UserGoalsProgress)
        .options(joinedload(UserGoalsProgress.goal))
        .order_by(UserGoalsProgress.id)
    )

    result = await session.execute(statement)
    progress_logs = result.scalars().all()
    return [UserGoalProgresSchema.model_validate(log) for log in progress_logs]


async def get_progress_logs_by_goal(
    goal_id: int, session: AsyncSession
) -> list[UserGoalProgresSchema]:
    statement = (
        select(UserGoalsProgress)
        .where(UserGoalsProgress.goal_id == goal_id)
        .options(joinedload(UserGoalsProgress.goal))
        .order_by(UserGoalsProgress.log_date.desc())
    )

    result = await session.execute(statement)
    progress_logs = result.scalars().all()

    return [UserGoalProgresSchema.model_validate(log) for log in progress_logs]


async def get_progress_log_by_id(
    log_id: int, session: AsyncSession
) -> UserGoalsProgress | None:
    statement = (
        select(UserGoalsProgress)
        .where(UserGoalsProgress.id == log_id)
        .options(joinedload(UserGoalsProgress.goal))
    )

    result = await session.execute(statement)
    return result.scalar_one_or_none()


async def create_progress_log(
    session: AsyncSession, data: UserGoalProgressCreate
) -> UserGoalsProgress:
    progress_data = data.model_dump(exclude={"goal"})
    progress_log = UserGoalsProgress(**progress_data)

    session.add(progress_log)
    await session.commit()
    statement = (
        select(UserGoalsProgress)
        .where(UserGoalsProgress.id == progress_log.id)
        .options(joinedload(UserGoalsProgress.goal))
    )

    result = await session.execute(statement)
    return result.scalar_one()


async def update_progress_log(
    session: AsyncSession,
    progress_log: UserGoalsProgress,
    progress_update: UserGoalProgressUpdate | UserGoalProgressUpdatePartial,
    partial: bool = False,
) -> UserGoalsProgress:
    update_data = progress_update.model_dump(exclude_unset=partial)

    for key, value in update_data.items():
        setattr(progress_log, key, value)
    await session.commit()
    await session.refresh(progress_log)
    return progress_log


async def delete_progress_log(session: AsyncSession, log_id: int) -> bool:
    result = await session.execute(
        select(UserGoalsProgress).where(UserGoalsProgress.id == log_id)
    )
    progress_log = result.scalar_one_or_none()

    if progress_log is None:
        return False

    await session.delete(progress_log)
    await session.commit()
    return True
