import json

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import db_helper
from core.redis_config import redis_client
from entities.reading_sessions.schema import (
    ReadingSessionCreate,
    ReadingSessionSchema,
    ReadingSessionUpdatePartial,
)
from entities.session_reactions.schema import (
    SessionReactionBase,
    SessionReactionToggleResponse,
)
from . import crud

router = APIRouter(tags=["Reading Session"])


@router.get("/", response_model=list[ReadingSessionSchema])
async def get_all_reading_sessions(
    current_username: str | None = Query(
        None, description="ID поточного користувача для позначення власних реакцій"
    ),
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    current_user_id = (
        await crud.get_user_id_by_username(session, current_username)
        if current_username
        else None
    )

    cache_key = (
        f"reading_sessions:all:user:{current_username}"
        if current_username
        else "reading_sessions:all"
    )
    cached = await redis_client.get(cache_key)

    if cached:
        logger.info(f"Get reading sessions from Redis cache (user: {current_username})")
        return json.loads(cached)

    data = await crud.get_all_reading_sessions(session, current_user_id=current_user_id)
    serialized_data = json.dumps([item.model_dump(mode="json") for item in data])

    logger.info("Return all reading sessions from db")
    await redis_client.set(cache_key, serialized_data, ex=300)
    return data


@router.get("/active", response_model=list[ReadingSessionSchema])
async def get_active_reading_sessions(
    current_username: str | None = Query(
        None,
        description="Username поточного користувача для позначення власних реакцій",
    ),
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    current_user_id = (
        await crud.get_user_id_by_username(session, current_username)
        if current_username
        else None
    )

    cache_key = (
        f"reading_sessions:active:user:{current_username}"
        if current_username
        else "reading_sessions:active"
    )

    cached = await redis_client.get(cache_key)

    if cached:
        logger.info(
            f"Get active reading sessions from Redis cache (user: {current_username})"
        )
        return json.loads(cached)

    data = await crud.get_active_reading_sessions(
        session, current_user_id=current_user_id
    )
    serialized_data = json.dumps([item.model_dump(mode="json") for item in data])

    await redis_client.set(cache_key, serialized_data, ex=10)
    return data


@router.get("/by-username", response_model=list[ReadingSessionSchema])
async def get_reading_sessions_by_username(
    username: str,
    limit: int = Query(20, ge=1, le=100),
    current_username: str | None = Query(None),
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    current_user_id = (
        await crud.get_user_id_by_username(session, current_username)
        if current_username
        else None
    )

    cache_key = (
        f"reading_sessions:user:{username}:by:{current_username}"
        if current_username
        else f"reading_sessions:user:{username}"
    )
    cached = await redis_client.get(cache_key)

    if cached:
        logger.info(
            f"Get all reading sessions for user {username}, limit={limit} from cache"
        )
        return json.loads(cached)[:limit]

    data = await crud.get_user_reading_session(
        username, session, limit, current_user_id=current_user_id
    )
    serialized_data = json.dumps([item.model_dump(mode="json") for item in data])

    logger.info(f"Return all reading sessions for user {username} with limit {limit}")
    await redis_client.set(cache_key, serialized_data, ex=300)
    return data


@router.get("/by-user-book", response_model=list[ReadingSessionSchema])
async def get_user_book_sessions(
    username: str,
    book_id: int,
    current_username: str | None = Query(None),
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    current_user_id = (
        await crud.get_user_id_by_username(session, current_username)
        if current_username
        else None
    )

    cache_key = (
        f"reading_sessions:user:{username}:book:{book_id}:by:{current_username}"
        if current_username
        else f"reading_sessions:user:{username}:book:{book_id}"
    )
    cached = await redis_client.get(cache_key)

    if cached:
        logger.info(
            f"Get all reading sessions for user {username} and book {book_id} from cache"
        )
        return json.loads(cached)

    data = await crud.get_user_book_reading_session(
        username, book_id, session, current_user_id=current_user_id
    )

    serialized_data = json.dumps([item.model_dump(mode="json") for item in data])
    logger.info(f"Return all reading sessions for user {username} and book {book_id}")

    await redis_client.set(cache_key, serialized_data, ex=300)
    return data


@router.get("/calendar/{username}")
async def get_user_calendar_sessions(
    username: str,
    year: int,
    month: int,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    data = await crud.get_user_monthly_reading_sessions(username, year, month, session)
    logger.info(
        f"Return calendar sessions for user {username} ({year}-{month}) from DB"
    )
    return data


@router.post(
    "/", response_model=ReadingSessionSchema, status_code=status.HTTP_201_CREATED
)
async def create_reading_session(
    data: ReadingSessionCreate,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    reading_session = await crud.create_reading_session(session, data)

    await redis_client.delete("reading_sessions:all")
    await redis_client.delete("reading_sessions:active")
    await redis_client.delete(f"reading_sessions:{reading_session.id}")

    return crud.map_session_to_schema(
        reading_session, current_user_id=str(reading_session.user_id)
    )


@router.get("/{session_id}", response_model=ReadingSessionSchema)
async def get_reading_session_by_id(
    session_id: int,
    current_username: str | None = Query(None),
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    current_user_id = (
        await crud.get_user_id_by_username(session, current_username)
        if current_username
        else None
    )

    cache_key = (
        f"reading_sessions:{session_id}:user:{current_username}"
        if current_username
        else f"reading_sessions:{session_id}"
    )
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
    mapped_schema = crud.map_session_to_schema(
        db_session, current_user_id=current_user_id
    )
    await redis_client.set(cache_key, mapped_schema.model_dump_json(), ex=300)
    return mapped_schema


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

    await redis_client.delete(f"reading_sessions:{session_id}")
    await redis_client.delete("reading_sessions:all")
    await redis_client.delete("reading_sessions:active")

    return crud.map_session_to_schema(updated_session)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reading_session_by_id(
    session_id: int,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    deleted = await crud.delete_reading_session(session, session_id)

    if deleted:
        try:
            await redis_client.delete("reading_sessions:all")
            await redis_client.delete("reading_sessions:active")
            await redis_client.delete(f"reading_sessions:{session_id}")
        except Exception as e:
            logger.error(f"Error invalidating Redis cache on delete session: {e}")


@router.post("/{session_id}/reactions", response_model=SessionReactionToggleResponse)
async def toggle_session_reaction(
    session_id: int,
    username: str = Query(
        ..., description="Username користувача, який ставить реакцію"
    ),
    reaction_data: SessionReactionBase = None,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    db_session = await crud.get_reading_session_by_id(session, session_id)
    if not db_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Reading Session Not Found"
        )

    user_id = await crud.get_user_id_by_username(session, username)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User Not Found"
        )

    action = await crud.toggle_session_reaction(
        session=session,
        session_id=session_id,
        user_id=str(user_id),
        emoji=reaction_data.emoji,
    )

    await redis_client.delete(f"reading_sessions:{session_id}")
    await redis_client.delete("reading_sessions:all")
    await redis_client.delete("reading_sessions:active")

    return SessionReactionToggleResponse(
        status=action,
        emoji=reaction_data.emoji,
        session_id=session_id,
    )
