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
