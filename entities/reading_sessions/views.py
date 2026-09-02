import json

from loguru import logger
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
        logger.info(f"Get reading sessions from Redis cache")
        return json.loads(cached)

    data = await crud.get_all_reading_sessions(session)
    serialized_data = json.dumps([item.model_dump(mode="json") for item in data])
    logger.info("Return all reading sessions from db")
    await redis_client.set(cache_key, serialized_data, ex=300)
    return data


@router.get("/by-username", response_model=list[ReadingSessionSchema])
async def get_reading_sessions_by_username(
    username: str,
    limit: int,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    cache_key = f"reading_sessions:user:{username}"
    cached = await redis_client.get(cache_key)

    if cached:
        logger.info(f"Get all reading sessions for user {username}, limit={limit}")
        return json.loads(cached)[:limit]

    data = await crud.get_user_reading_session(username, session, limit)
    serialized_data = json.dumps([item.model_dump(mode="json") for item in data])
    logger.info(f"Return all reading sessions for user {username} with limit {limit}")
    await redis_client.set(cache_key, serialized_data, ex=300)
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
        logger.info(f"Get all reading sessions for user {username} and book {book_id}")
        return json.loads(cached)

    data = await crud.get_user_book_reading_session(username, book_id, session)

    serialized_data = json.dumps([item.model_dump(mode="json") for item in data])
    logger.info(f"Return all reading sessions for user {username} and book {book_id}")

    await redis_client.set(cache_key, serialized_data, ex=300)
    return data


@router.get("/{session_id}", response_model=ReadingSessionSchema)
async def get_reading_session_by_id(
    session_id: int,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    cache_key = f"reading_sessions:{session_id}"
    cached = await redis_client.get(cache_key)

    if cached:
        logger.info(f"Get reading session with id {session_id} from Redis cache")
        return json.loads(cached)

    db_session = await crud.get_reading_session_by_id(session, session_id)

    if not db_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Reading Session Not Found"
        )

    logger.info(f"Return reading session {session_id} from db")
    result = ReadingSessionSchema.model_validate(db_session)
    await redis_client.set(cache_key, result.model_dump_json(), ex=300)
    return result


@router.post("/", response_model=ReadingSessionSchema, status_code=201)
async def create_reading_session(
    data: ReadingSessionCreate,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    reading_session = await crud.create_reading_session(session, data)
    await redis_client.delete("reading_sessions:all")

    return reading_session


@router.patch("/{session_id}", response_model=ReadingSessionSchema)
async def update_reading_session(
    session_id: int,
    data: ReadingSessionUpdatePartial,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    reading_session = await crud.get_reading_session_by_id(session, session_id)

    if not reading_session:
        logger.error(
            f"Failed to update reading session with id {session_id} - reading session was not found"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Reading Session Not Found"
        )

    updated_session = await crud.update_reading_session(
        session, reading_session, data, partial=True
    )

    return updated_session


@router.delete("/{session_id}")
async def delete_reading_session_by_id(
    session_id: int,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    deleted = await crud.delete_reading_session(session, session_id)

    if deleted:
        try:
            await redis_client.delete(f"reading_sessions:all")
            await redis_client.delete(f"reading_sessions:{session_id}")
        except Exception:
            return
