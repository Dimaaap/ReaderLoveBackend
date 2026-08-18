import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.redis_config import redis_client
from core.models import db_helper
from entities.book_authors.schema import (
    BookAuthorsSchema,
    BookAuthorsCreate,
    BookAuthorsUpdatePartial,
)
from . import crud

router = APIRouter(tags=["Book Authors"])


async def invalidate_book_authors_cache():
    keys = []

    async for key in redis_client.scan_iter(match="book_authors:*"):
        keys.append(key)

    if keys:
        await redis_client.delete(*keys)


@router.get("/", response_model=list[BookAuthorsSchema])
async def get_all(
    limit: int = Query(default=10, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    cache_key = f"book_authors:limit:{limit}:offset:{offset}"

    cached = await redis_client.get(cache_key)

    if cached:
        return json.loads(cached)

    data = await crud.get_all_authors(session=session, limit=limit, offset=offset)
    result = [BookAuthorsSchema.model_validate(author) for author in data]

    serialized = [item.model_dump(mode="json") for item in result]

    await redis_client.set(
        cache_key,
        json.dumps(serialized),
        ex=300,
    )
    return result


@router.get("/{author_id}")
async def get_author_by_id(
    author_id: int, session: AsyncSession = Depends(db_helper.scoped_session_dependency)
):
    cache_key = f"book_authors:{author_id}"

    cached = await redis_client.get(cache_key)

    if cached:
        return json.loads(cached)

    data = await crud.get_author_by_id(session, author_id)

    if data:
        result = BookAuthorsSchema.model_validate(data)

        await redis_client.set(cache_key, result.model_dump_json(), ex=300)
        return result

    return data


@router.post("/", response_model=BookAuthorsCreate, status_code=201)
async def create_author_view(
    data: BookAuthorsCreate,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    book_author = await crud.create_author(session, data)

    await invalidate_book_authors_cache()
    return book_author


@router.delete("/{author_id}")
async def delete_author_by_id_view(
    author_id: int, session: AsyncSession = Depends(db_helper.scoped_session_dependency)
):
    deleted = await crud.delete_author(session, author_id)

    if deleted:
        try:
            await invalidate_book_authors_cache()
        except Exception:
            return


@router.patch("/{author_id}", response_model=BookAuthorsUpdatePartial)
async def update_author_view(
    author_id: int,
    data: BookAuthorsUpdatePartial,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    updated = await crud.partial_update_author(session, author_id, data)

    if not updated:
        raise HTTPException(status_code=404, detail="Author is not found")

    await invalidate_book_authors_cache()

    return updated
