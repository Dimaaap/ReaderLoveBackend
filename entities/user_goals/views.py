from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import db_helper
from entities.user_goals.schema import (
    UserGoalCreate,
    UserGoalSchema,
    UserGoalUpdatePartial,
)

from . import crud

router = APIRouter(tags=["User Goals"])


@router.get("/", response_model=list[UserGoalSchema])
async def get_all_user_goals(
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    data = await crud.get_all_user_goals(session)
    return data


@router.post("/", response_model=UserGoalSchema, status_code=status.HTTP_201_CREATED)
async def create_user_goal_view(
    data: UserGoalCreate,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    user_goal = await crud.create_goal(session, data)
    return user_goal


@router.get("/by-username", response_model=list[UserGoalSchema])
async def get_user_goals_by_username(
    username: str, session: AsyncSession = Depends(db_helper.scoped_session_dependency)
):
    data = await crud.get_user_goals_with_progress(username, session)
    return data


@router.get("/{goal_id}", response_model=UserGoalSchema)
async def get_user_goal_by_id(
    goal_id: int, session: AsyncSession = Depends(db_helper.scoped_session_dependency)
):
    goal = await crud.get_goal_by_id(goal_id, session)
    if not goal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User goal is not found"
        )

    return UserGoalSchema.model_validate(goal)


@router.patch("/{goal_id}", response_model=UserGoalSchema)
async def update_goal(
    goal_id: int,
    data: UserGoalUpdatePartial,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    goal = await crud.get_goal_by_id(goal_id, session)

    if not goal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User goal with id {goal_id} is not found",
        )

    updated_goal = await crud.update_goal(session, goal, data, partial=True)

    return updated_goal


@router.delete("/{goal_id}")
async def delete_goal_by_id(
    goal_id: int, session: AsyncSession = Depends(db_helper.scoped_session_dependency)
):
    is_deleted = await crud.delete_goal(session, goal_id)
    return is_deleted
