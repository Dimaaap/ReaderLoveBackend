import json

from loguru import logger
from fastapi import APIRouter, Depends, HTTPException, Query, status
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
    keys = [key async for key in redis_client.scan_iter(match="book_authors:*")]

    if keys:
        await redis_client.delete(*keys)


async def invalidate_countries_cache():
    keys = [key async for key in redis_client.scan_iter(match="countries:*")]

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
        logger.info("Get all book authors from Redis cache")
        return json.loads(cached)

    result = await crud.get_all_authors(
        session=session,
        limit=limit,
        offset=offset,
    )

    serialized = [author.model_dump(mode="json") for author in result]

    await redis_client.set(
        cache_key,
        json.dumps(serialized, ensure_ascii=False),
        ex=300,
    )

    return serialized


@router.get("/{author_id}", response_model=BookAuthorsSchema)
async def get_author_by_id(
    author_id: int,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    cache_key = f"book_authors:{author_id}"

    cached = await redis_client.get(cache_key)

    if cached:
        logger.info(f"Get author {author_id} from Redis cache")
        return json.loads(cached)

    author = await crud.get_author_by_id(session, author_id)

    if author is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Author not found",
        )

    await redis_client.set(
        cache_key,
        author.model_dump_json(),
        ex=300,
    )

    return author


@router.post(
    "/",
    response_model=BookAuthorsSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_author_view(
    data: BookAuthorsCreate,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    author = await crud.create_author(session, data)

    await invalidate_book_authors_cache()
    await invalidate_countries_cache()

    return author


@router.delete(
    "/{author_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_author_by_id_view(
    author_id: int,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    deleted = await crud.delete_author(session, author_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Author not found",
        )

    await invalidate_book_authors_cache()
    await invalidate_countries_cache()


@router.patch("/{author_id}", response_model=BookAuthorsSchema)
async def update_author_view(
    author_id: int,
    data: BookAuthorsUpdatePartial,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    updated = await crud.partial_update_author(
        session,
        author_id,
        data,
    )

    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Author not found",
        )

    await invalidate_book_authors_cache()
    await invalidate_countries_cache()

    return updated
