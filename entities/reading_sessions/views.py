import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.redis_config import redis_client
from core.models import db_helper
from entities.reading_sessions.schema import (
    ReadingSessionCreate,
    ReadingSessionSchema,
    ReadingSessionUpdatePartial,
)
from . import crud

router = APIRouter(tags=["Reading Session"])


@router.get("/", response_model=list[ReadingSessionSchema])
async def get_all_reading_sessions(
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    cache_key = "reading_sessions:all"
    cached = await redis_client.get(cache_key)

    if cached:
        return json.loads(cached)

    data = await crud.get_all_reading_sessions(session)
    await redis_client.set(
        cache_key, json.dumps([item.model_dump() for item in data]), ex=300
    )
    return data


@router.get("/by-user-book", response_model=list[ReadingSessionSchema])
async def get_user_book_sessions(
    username: str,
    book_id: int,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    cache_key = f"reading_sessions:user:{username}:book:{book_id}"
    cached = await redis_client.get(cache_key)

    if cached:
        return json.loads(cached)

    data = await crud.get_user_book_reading_session(username, book_id, session)

    await redis_client.set(
        cache_key, json.dumps([item.model_dump() for item in data]), ex=300
    )
    return data


@router.get("/{session_id}", response_model=ReadingSessionSchema)
async def get_reading_session_by_id(
    session_id: int,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    cache_key = f"reading_sessions:{session_id}"
    cached = await redis_client.get(cache_key)

    if cached:
        return json.loads(cached)

    db_session = await crud.get_reading_session_by_id(session, session_id)

    if not db_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Reading Session Not Found"
        )

    result = ReadingSessionSchema.model_validate(db_session)
    await redis_client.set(cache_key, result.model_dump_json(), ex=300)
    return result