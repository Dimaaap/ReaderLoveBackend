from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import db_helper
from entities.user_goals_progress.schema import (
    UserGoalProgressCreate,
    UserGoalProgressUpdatePartial,
    UserGoalProgresSchema,
)

from . import crud

router = APIRouter(tags=["User Goals Progress"])


@router.get("/", response_model=list[UserGoalProgresSchema])
async def get_user_goals_progress(
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    return await crud.get_all_goal_progresses(session)


@router.post(
    "/", response_model=UserGoalProgresSchema, status_code=status.HTTP_201_CREATED
)
async def create_user_goals_progress(
    data: UserGoalProgressCreate,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    return await crud.create_progress_log(session, data)


@router.get("/by-goal/{goal_id}", response_model=list[UserGoalProgresSchema])
async def get_user_goals_progress_by_goal(
    goal_id: int, session: AsyncSession = Depends(db_helper.scoped_session_dependency)
):
    return await crud.get_progress_logs_by_goal(goal_id, session)


@router.get("{/log_id}", response_model=UserGoalProgresSchema)
async def get_user_goal_progress_by_id(
    log_id: int, session: AsyncSession = Depends(db_helper.scoped_session_dependency)
):
    log = await crud.get_progress_log_by_id(log_id, session)

    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User goal progress was not found",
        )

    return UserGoalProgresSchema.model_validate(log)


@router.patch("/{log_id}", response_model=UserGoalProgresSchema)
async def update_goal_progress(
    log_id: int,
    data: UserGoalProgressUpdatePartial,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    goal_progress = await crud.get_progress_log_by_id(log_id, session)

    if not goal_progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User goal progress was not found",
        )

    updated_progress = await crud.update_progress_log(
        session, goal_progress, data, partial=True
    )

    return updated_progress


@router.delete("/{log_id}")
async def delete_goal_progress_by_id(
    log_id: int, session: AsyncSession = Depends(db_helper.scoped_session_dependency)
):
    is_deleted = await crud.delete_progress_log(session, log_id)
    return is_deleted
