from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from core.models import db_helper
from entities.stats.schema import UserStatisticsResponse

from . import crud

router = APIRouter(prefix="", tags=["Statistics"])


@router.get("/{username}/", response_model=UserStatisticsResponse)
async def get_user_statistics(
    username: str,
    period: Literal["7d", "1m", "3m", "1y", "all"] = Query(default="3m"),
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    stats = await crud.get_user_reading_statistics(session, username, period)
    if not stats:
        raise HTTPException(
            status_code=404, detail="User not found or no stats available"
        )
    return stats
