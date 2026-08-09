import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.redis_config import redis_client
from core.models import db_helper
from entities.book_genres.schema import (
    BookGenreSchema,
    BookGenreCreate,
    BookGenreUpdatePartial,
    BookGenresWithBookSchema,
)
from . import crud

router = APIRouter(tags=["Book Genres"])


@router.get("/", response_model=list[BookGenreSchema])
async def get_all(session: AsyncSession = Depends(db_helper.scoped_session_dependency)):
    cache_key = "book_genres:all"

    cached = await redis_client.get(cache_key)

    if cached:
        return json.loads(cached)

    data = await crud.get_all_genres(session)
    result = [BookGenreSchema.model_validate(genre) for genre in data]

    await redis_client.set(cache_key, json.dumps([item.model_dump() for item in data]))

    return result


@router.get("/{genre_id}")
async def get_genre_by_id(
    genre_id: int, session: AsyncSession = Depends(db_helper.scoped_session_dependency)
):
    cache_key = f"book_genres:{genre_id}"

    cached = await redis_client.get(cache_key)

    if cached:
        return json.loads(cached)

    data = await crud.get_genre_by_id(session, genre_id)

    if data:
        result = BookGenreSchema.model_validate(data)

        await redis_client.set(cache_key, result.model_dump_json(), ex=300)

        return result
    return data


@router.get("/by-slug/{genre_slug}")
async def get_genre_by_slug(
    genre_slug: str,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    cache_key = f"book_genres:slug:{genre_slug}"

    cached = await redis_client.get(cache_key)

    if cached:
        return json.loads(cached)

    data = await crud.get_genre_by_slug(session, genre_slug)

    if data:
        result = BookGenresWithBookSchema.model_validate(data)
        await redis_client.set(cache_key, result.model_dump_json(), ex=300)

        return result
    return data


@router.post("/", response_model=BookGenreCreate, status_code=201)
async def create_genre_view(
    data: BookGenreCreate,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    book_genre = await crud.create_genre(session, data)

    await redis_client.delete("book_genres:all")
    return book_genre


@router.delete("/{genre_id}")
async def delete_book_genre_by_id_view(
    genre_id: int, session: AsyncSession = Depends(db_helper.scoped_session_dependency)
):
    deleted = await crud.delete_genre(session, genre_id)

    if deleted:
        try:
            await redis_client.delete(f"book_genres:{genre_id}")
            await redis_client.delete(f"book_genres:all")
        except Exception:
            return

    return {"ok": True}


@router.patch("/{genre_id}", response_model=BookGenreUpdatePartial)
async def update_genre_view(
    genre_id: int,
    data: BookGenreUpdatePartial,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    updated = await crud.partial_update_genre(session, genre_id, data)

    if not updated:
        raise HTTPException(status_code=404, detail="Genre is not found")

    await redis_client.delete(f"book_genres:all")
    await redis_client.delete(f"book_genres:{genre_id}")

    return updated
