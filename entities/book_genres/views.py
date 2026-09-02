import json

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from core.redis_config import redis_client
from core.models import db_helper
from entities.book_genres.schema import (
    BookGenreSchema,
    BookGenreCreate,
    BookGenreUpdatePartial,
)
from . import crud

router = APIRouter(tags=["Book Genres"])


async def invalidate_book_genres_cache():
    keys = []

    async for key in redis_client.scan_iter(match="book_genres:*"):
        keys.append(key)

    if keys:
        await redis_client.delete(*keys)


@router.get("/", response_model=list[BookGenreSchema])
async def get_all(
    limit: int = Query(default=10, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    cache_key = f"book_genres:limit:{limit}:offset:{offset}"

    cached = await redis_client.get(cache_key)

    if cached:
        logger.info(f"Got book genres list from Redis cache")
        return json.loads(cached)

    data = await crud.get_all_genres(session=session, limit=limit, offset=offset)
    result = [BookGenreSchema.model_validate(genre) for genre in data]

    serialized = [item.model_dump(mode="json") for item in result]
    logger.info("Return all book genres from db")

    await redis_client.set(
        cache_key,
        json.dumps(serialized),
        ex=300,
    )

    return result


@router.get("/{genre_id}")
async def get_genre_by_id(
    genre_id: int, session: AsyncSession = Depends(db_helper.scoped_session_dependency)
):
    cache_key = f"book_genres:{genre_id}"

    cached = await redis_client.get(cache_key)

    if cached:
        logger.info(f"Get book genre with id {genre_id} from Redis cache")
        return json.loads(cached)

    data = await crud.get_genre_by_id(session, genre_id)

    result = BookGenreSchema.model_validate(data)
    logger.info(f"Return book genre with id {genre_id} from db")

    await redis_client.set(
        cache_key,
        json.dumps(result.model_dump(mode="json")),
        ex=300,
    )

    return result


@router.get("/by-slug/{genre_slug}")
async def get_genre_by_slug(
    genre_slug: str,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    cache_key = f"book_genres:slug:{genre_slug}"

    cached = await redis_client.get(cache_key)

    if cached:
        logger.info(f"Get book genre by slug {genre_slug} from Redis cache")
        return json.loads(cached)

    data = await crud.get_genre_by_slug(session, genre_slug)

    if data is None:
        return None

    result = BookGenreSchema.model_validate(data)
    logger.info(f"Return book genre by slug {genre_slug} from db")

    await redis_client.set(
        cache_key,
        json.dumps(result.model_dump(mode="json")),
        ex=300,
    )

    return result


@router.post("/", response_model=BookGenreCreate, status_code=201)
async def create_genre_view(
    data: BookGenreCreate,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    book_genre = await crud.create_genre(session, data)

    await invalidate_book_genres_cache()
    logger.info("Created new book genre")
    return book_genre


@router.delete("/{genre_id}")
async def delete_book_genre_by_id_view(
    genre_id: int, session: AsyncSession = Depends(db_helper.scoped_session_dependency)
):
    (deleted,) = await crud.delete_genre(session, genre_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book Genre is not found",
        )

    await invalidate_book_genres_cache()
    logger.info(f"Successfully deleted book genre with id {genre_id}")

    return {
        "ok": True,
        "genre_id": genre_id,
    }


@router.patch("/{genre_id}", response_model=BookGenreUpdatePartial)
async def update_genre_view(
    genre_id: int,
    data: BookGenreUpdatePartial,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    updated = await crud.partial_update_genre(session, genre_id, data)

    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book Genre is not found",
        )

    await invalidate_book_genres_cache()
    logger.info(f"Successfully updated book genre with id {genre_id}, data - {data}")

    return updated
