import json
import io
from pathlib import Path
from uuid import uuid4
from typing import Optional
from loguru import logger

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import User, db_helper
from entities.book_selections.schema import (
    BookSelectionSchema,
    BookSelectionCreate,
    BookSelectionUpdatePartial,
    BookSelectionSummarySchema,
    BookSelectionWithDetailsSchema,
)
from core.redis_config import redis_client
from . import crud

MEDIA_DIR = Path("media/book_selections")
MEDIA_DIR.mkdir(parents=True, exist_ok=True)
MAX_COVER_SIZE = 5 * 1024 * 1024

router = APIRouter(prefix="/book_selections", tags=["Book Selections"])


@router.get("/", response_model=list[BookSelectionSummarySchema])
async def get_all_book_selections(
    is_active: Optional[bool] = Query(default=True),
    limit: Optional[int] = Query(default=None, ge=1, le=100),
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    cache_key = f"selections:all:active:{is_active}:limit:{limit}"

    cached = await redis_client.get(cache_key)
    if cached:
        logger.info(
            f"Get all book selections (is_active={is_active}, limit={limit}) from Redis cache"
        )
        return json.loads(cached)

    selections = await crud.get_book_selections_with_summaries(
        session=session, is_active=is_active, limit=limit
    )

    logger.info(
        f"Return all book selections (is_active={is_active}, limit={limit}) from db"
    )
    await redis_client.set(
        cache_key, json.dumps([s.model_dump() for s in selections]), ex=600
    )
    return selections
