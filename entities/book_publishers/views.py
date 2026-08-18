import json

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.redis_config import redis_client
from core.models import db_helper

from entities.book_publishers.schema import (
    BookPublisherSchema,
    BookPublisherCreate,
    BookPublisherUpdatePublisher,
)
from . import crud
from ..book_genres.schema import BookGenreSchema

router = APIRouter(tags=["Book Publishers"])


async def invalidate_book_publishers_cache():
    keys = []

    async for key in redis_client.scan_iter(match="book_publishers:*"):
        keys.append(key)

    if keys:
        await redis_client.delete(*keys)


@router.get("/", response_model=list[BookGenreSchema])
async def get_all_publishers(
    limit: int = Query(default=10, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    cache_key = f"book_publishers:limit:{limit}:offset:{offset}"

    cached = await redis_client.get(cache_key)

    if cached:
        return json.loads(cached)

    data = await crud.get_all_book_publishers(
        session=session,
        limit=limit,
        offset=offset,
    )

    result = [BookPublisherSchema.model_validate(publisher) for publisher in data]

    serialized = [item.model_dump(mode="json") for item in result]

    await redis_client.set(
        cache_key,
        json.dumps(serialized),
        ex=300,
    )

    return result


@router.get("/{publisher_id}")
async def get_book_publisher_by_id(
    publisher_id: int,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    cache_key = f"book_publishers:{publisher_id}"
    cached = await redis_client.get(cache_key)

    if cached:
        return json.loads(cached)

    data = await crud.get_book_publisher_by_id(session, publisher_id)

    if data is None:
        return None

    result = BookPublisherSchema.model_validate(data)

    await redis_client.set(
        cache_key,
        json.dumps(result.model_dump(mode="json")),
        ex=300,
    )

    return result


@router.get("/by-slug/{publisher_slug}", response_model=BookPublisherSchema | None)
async def get_book_publisher_by_slug(
    publisher_slug: str,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    cache_key = f"book_publishers:slug:{publisher_slug}"
    cached = await redis_client.get(cache_key)

    if cached:
        return json.loads(cached)

    data = await crud.get_book_publisher_by_slug(session, publisher_slug)

    if data is None:
        return None

    result = BookPublisherSchema.model_validate(data)

    await redis_client.set(
        cache_key,
        json.dumps(result.model_dump(mode="json")),
        ex=300,
    )

    return result


@router.post(
    "/", response_model=BookPublisherCreate, status_code=status.HTTP_201_CREATED
)
async def create_book_publisher_view(
    data: BookPublisherCreate,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    book_publisher = await crud.create_book_publisher(session, data)
    await invalidate_book_publishers_cache()
    return book_publisher


@router.delete("/{publisher_id}")
async def delete_book_publisher_by_id_view(
    publisher_id: int,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    deleted, publisher = await crud.delete_book_publisher(session, publisher_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book Publisher is not found",
        )
    await invalidate_book_publishers_cache()

    return {
        "ok": True,
        "publisher_id": publisher_id,
    }


@router.patch("/{publisher_id}", response_model=BookPublisherUpdatePublisher)
async def update_book_publisher(
    publisher_id: int,
    data: BookPublisherUpdatePublisher,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    updated = await crud.update_book_publisher(
        session, publisher_id, data, partial=True
    )

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Book Publisher is not found"
        )

    await invalidate_book_publishers_cache()

    return updated
