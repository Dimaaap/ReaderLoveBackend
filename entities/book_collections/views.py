import json
from loguru import logger
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.redis_config import redis_client
from core.models import db_helper
from entities.book_collections.schema import (
    BookCollectionSchema,
    BookCollectionCreate,
    BookCollectionUpdatePartial,
    BookCollectionWithDetailsSchema,
)
from . import crud

router = APIRouter(tags=["Book Collection"])


@router.get("/{username}", response_model=list[BookCollectionSchema])
async def get_user_collections(
    username: str, session: AsyncSession = Depends(db_helper.scoped_session_dependency)
):
    cache_key = f"collections:user:{username}"

    cached = await redis_client.get(cache_key)

    if cached:
        logger.info(f"Get collections for user {username} from Redis cache")
        return json.loads(cached)

    collections = await crud.get_user_collections(session, username)
    result = [BookCollectionSchema.model_validate(col) for col in collections]

    logger.info(f"Return collections for user {username} from db")

    await redis_client.set(
        cache_key, json.dumps([c.model_dump(mode="json") for c in result]), ex=300
    )

    return result


@router.get("/detail/{collection_id}", response_model=BookCollectionWithDetailsSchema)
async def get_collection_detail(
    collection_id: int,
    username: str,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    cache_key = f"collection:{collection_id}:user:{username}"

    cached = await redis_client.get(cache_key)
    if cached:
        logger.info(
            f"Get collection detail id {collection_id} for user {username} from Redis cache"
        )
        return json.loads(cached)

    collection = await crud.get_collection_by_id(session, collection_id, username)

    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Колекцію не знайдено"
        )

    result = BookCollectionWithDetailsSchema.model_validate(collection)
    logger.info(
        f"Return collection detail id {collection_id} for user {username} from db"
    )

    await redis_client.set(cache_key, result.model_dump_json(), ex=300)
    return result


@router.post(
    "/{username}",
    response_model=BookCollectionWithDetailsSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_collection(
    username: str,
    data: BookCollectionCreate,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    new_collection = await crud.create_collection(session, username, data)
    logger.info(f"Created collection '{data.title}' for user {username}")

    await redis_client.delete(f"collections:user:{username}")
    return new_collection


@router.patch(
    "/{collection_id}/{username}", response_model=BookCollectionWithDetailsSchema
)
async def update_collection(
    collection_id: int,
    username: str,
    data: BookCollectionUpdatePartial,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    collection = await crud.get_collection_by_id(session, collection_id, username)

    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Колекцію не знайдено"
        )

    updated_collection = await crud.update_collection(
        session, collection, data, partial=True
    )

    await redis_client.delete(f"collections:user:{username}")
    await redis_client.delete(f"collection:{collection_id}:user:{username}")

    return updated_collection


@router.delete("/{collection_id}/{username}", status_code=status.HTTP_200_OK)
async def delete_collection(
    collection_id: int,
    username: str,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    deleted = await crud.delete_collection(session, collection_id, username)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Колекцію не знайдено"
        )

    await redis_client.delete(f"collections:user:{username}")
    await redis_client.delete(f"collection:{collection_id}:user:{username}")

    return {"ok": True}


@router.post(
    "/{collection_id}/books/{book_id}/{username}",
    response_model=BookCollectionWithDetailsSchema,
)
async def add_book_to_collection_view(
    collection_id: int,
    book_id: int,
    username: str,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    collection = await crud.add_book_to_collection(
        session, collection_id, book_id, username
    )

    await redis_client.delete(f"collections:user:{username}")
    await redis_client.delete(f"collection:{collection_id}:user:{username}")

    return collection


@router.delete(
    "/{collection_id}/books/{book_id}/{username}",
    response_model=BookCollectionWithDetailsSchema,
)
async def remove_book_from_collection_view(
    collection_id: int,
    book_id: int,
    username: str,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    collection = await crud.remove_book_from_collection(
        session, collection_id, book_id, username
    )

    await redis_client.delete(f"collections:user:{username}")
    await redis_client.delete(f"collection:{collection_id}:user:{username}")

    return collection
