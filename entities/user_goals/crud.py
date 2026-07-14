from datetime import datetime

from sqlalchemy import select, func, extract
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from core.models import UserGoals, UserGoalsProgress, User
from core.models.user_goals import GoalPeriod
from entities.user_goals.schema import (
    UserGoalSchema,
    UserGoalCreate,
    UserGoalUpdate,
    UserGoalUpdatePartial,
)


async def get_all_user_goals(session: AsyncSession) -> list[UserGoals]:
    statement = (
        select(UserGoals).options(joinedload(UserGoals.user)).order_by(UserGoals.id)
    )

    result = await session.execute(statement)
    return list(result.scalars().all())


async def get_goal_by_id(goal_id: int, session: AsyncSession) -> UserGoals | None:
    statement = (
        select(UserGoals)
        .where(UserGoals.id == goal_id)
        .options(joinedload(UserGoals.user))
    )

    result = await session.execute(statement)
    return result.scalar_one_or_none()


async def get_user_goals_with_progress(
    username: str, session: AsyncSession
) -> list[dict]:
    today = datetime.now()

    statement = (
        select(UserGoals)
        .join(UserGoals.user)
        .where(User.username == username)
        .options(joinedload(UserGoals.user))
        .order_by(UserGoals.created_at.desc())
    )

    result = await session.execute(statement)
    goals = result.scalars().all()

    goals_with_progress = []

    for goal in goals:
        progress_statement = select(func.sum(UserGoalsProgress.value)).where(
            UserGoalsProgress.goal_id == goal.id
        )

        if goal.period == GoalPeriod.DAILY:
            progress_statement = progress_statement.where(
                func.date(UserGoalsProgress.log_date) == today.date()
            )
        elif goal.period == GoalPeriod.MONTHLY:
            progress_statement = progress_statement.where(
                extract("month", UserGoalsProgress.log_date) == today.month,
                extract("year", UserGoalsProgress.log_date) == today.year,
            )
        elif goal.period == GoalPeriod.YEARLY:
            progress_statement = progress_statement.where(
                extract("year", UserGoalsProgress.log_date) == today.year
            )

        progress_result = await session.execute(progress_statement)
        current_value = progress_result.scalar() or 0

        is_completed = current_value >= goal.target_value

        if goal.is_completed != is_completed:
            goal.is_completed = is_completed
            session.add(goal)
            await session.commit()

        validated_goal = UserGoalSchema.model_validate(goal)
        goal_data = validated_goal.model_dump()

        goal_data["current_value"] = current_value
        goal_data["is_completed"] = is_completed

        goals_with_progress.append(goal_data)

    return goals_with_progress


async def create_goal(session: AsyncSession, data: UserGoalCreate) -> UserGoals:
    goal_data = data.model_dump(exclude={"user"})
    goal = UserGoals(**goal_data)

    session.add(goal)
    await session.commit()

    statement = (
        select(UserGoals)
        .where(UserGoals.id == goal.id)
        .options(joinedload(UserGoals.user))
    )
    result = await session.execute(statement)
    return result.scalar_one()


async def update_goal(
    session: AsyncSession,
    goal: UserGoals,
    goal_update: UserGoalUpdate | UserGoalUpdatePartial,
    partial: bool = False,
) -> UserGoals:
    update_data = goal_update.model_dump(exclude_unset=partial)

    for key, value in update_data.items():
        setattr(goal, key, value)

    await session.commit()
    await session.refresh(goal)
    return goal


async def delete_goal(session: AsyncSession, goal_id) -> bool:
    result = await session.execute(select(UserGoals).where(UserGoals.id == goal_id))

    goal = result.scalar_one_or_none()

    if goal is None:
        return False

    await session.delete(goal)
    await session.commit()
    return True
