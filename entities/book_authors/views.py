import json

from fastapi import APIRouter, Depends, HTTPException
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


@router.get("/", response_model=list[BookAuthorsSchema])
async def get_all(session: AsyncSession = Depends(db_helper.scoped_session_dependency)):
    cache_key = "book_authors:all"

    cached = await redis_client.get(cache_key)

    if cached:
        return json.loads(cached)

    data = await crud.get_all_authors(session)
    result = [BookAuthorsSchema.model_validate(author) for author in data]

    await redis_client.set(cache_key, json.dumps([item.model_dump() for item in data]))

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

    await redis_client.delete(f"book_authors:all")
    return book_author


@router.delete("/{author_id}")
async def delete_author_by_id_view(
    author_id: int, session: AsyncSession = Depends(db_helper.scoped_session_dependency)
):
    deleted = await crud.delete_author(session, author_id)

    if deleted:
        try:
            await redis_client.delete(f"book_authors:{author_id}")
            await redis_client.delete(f"book_authors:all")
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

    await redis_client.delete("book_authors:all")
    await redis_client.delete(f"book_authors:{author_id}")

    return updated
