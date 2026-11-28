from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import db_helper
from core.redis_config import redis_client
from . import crud
from .schema import (
    StreakMilestoneCreate,
    StreakMilestoneSchema,
    StreakMilestoneUpdatePartial,
)
from utils.auth import get_current_user_id
from entities.reading_streaks import crud as reading_streaks_crud

router = APIRouter(tags=["Reading Milestones"])


@router.get("/", response_model=list[StreakMilestoneSchema])
async def get_my_milestones(
    user_id: str = Depends(get_current_user_id),
    only_uncelebrated: bool = Query(
        False, description="Повертати лише ще не відсвятковані віхи"
    ),
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    logger.info(
        f"Getting milestones for user {user_id} (only_uncelebrated={only_uncelebrated})"
    )
    return await crud.get_user_milestones(session, user_id, only_uncelebrated)


@router.get("/uncelebrated", response_model=list[StreakMilestoneSchema])
async def get_uncelebrated_milestones(
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    logger.info(f"Getting uncelebrated milestones for user {user_id}")
    return await crud.get_user_milestones(session, user_id, only_uncelebrated=True)


@router.get("/{milestone_days}", response_model=StreakMilestoneSchema)
async def get_milestone_by_days(
    milestone_days: int,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    milestone = await crud.get_user_milestone_by_days(session, user_id, milestone_days)

    if not milestone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Milestone not found"
        )
    return milestone


@router.post(
    "/", response_model=StreakMilestoneSchema, status_code=status.HTTP_201_CREATED
)
async def create_user_milestone(
    milestone_days: int,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    streak, _ = await reading_streaks_crud.get_or_create_streak(session, user_id)

    payload = StreakMilestoneCreate(
        user_id=user_id, streak_id=streak.id, milestone_days=milestone_days
    )
    return await crud.create_milestone(session, payload)


@router.patch("/{milestone_days}", response_model=StreakMilestoneSchema)
async def patch_user_milestone(
    milestone_days: int,
    data: StreakMilestoneUpdatePartial,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    milestone = await crud.get_user_milestone_by_days(session, user_id, milestone_days)
    if not milestone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Milestone not found"
        )

    return await crud.update_milestone(
        session=session, milestone=milestone, milestone_update=data, partial=True
    )


@router.delete("/{milestone_days}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_milestone(
    milestone_days: int,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    deleted = await crud.delete_milestone(
        session=session, user_id=user_id, milestone_days=milestone_days
    )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Milestone not found"
        )

    return None
