import json
import io
from pathlib import Path
from uuid import uuid4
from typing import Optional
from loguru import logger

from fastapi import APIRouter, Depends, HTTPException, status, Query, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import db_helper
from entities.book_selections.schema import (
    BookSelectionSchema,
    BookSelectionCreate,
    BookSelectionUpdatePartial,
    BookSelectionSummarySchema,
    BookSelectionWithDetailsSchema,
)
from core.redis_config import redis_client
from . import crud

MEDIA_DIR = Path("media/book_selections")
MEDIA_DIR.mkdir(parents=True, exist_ok=True)
MAX_COVER_SIZE = 5 * 1024 * 1024

router = APIRouter(tags=["Book Selections"])


@router.get("/", response_model=list[BookSelectionSummarySchema])
async def get_all_book_selections(
    is_active: Optional[bool] = Query(default=True),
    limit: Optional[int] = Query(default=None, ge=1, le=100),
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    cache_key = f"selections:all:active:{is_active}:limit:{limit}"

    cached = await redis_client.get(cache_key)
    if cached:
        logger.info(
            f"Get all book selections (is_active={is_active}, limit={limit}) from Redis cache"
        )
        return json.loads(cached)

    selections = await crud.get_book_selections_with_summaries(
        session=session, is_active=is_active, limit=limit
    )

    logger.info(
        f"Return all book selections (is_active={is_active}, limit={limit}) from db"
    )
    await redis_client.set(
        cache_key, json.dumps([s.model_dump() for s in selections]), ex=600
    )
    return selections


@router.get("/{identifier}", response_model=BookSelectionWithDetailsSchema)
async def get_book_selection_by_id_or_slug(
    identifier: str,
    username: Optional[str] = Query(default=None),
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    cache_key = (
        f"selection:{identifier}:user:{username}"
        if username
        else f"selection:{identifier}"
    )

    cached = await redis_client.get(cache_key)
    if cached:
        logger.info(
            f"Get selection '{identifier}' (username={username}) from Redis cache"
        )
        return json.loads(cached)

    selection = await crud.get_book_selection_by_id_or_slug(
        session=session, identifier=identifier, user_id=username, with_details=True
    )

    if not selection:
        logger.error(f"Failed to get book selection '{identifier}' - Not found in db")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Book selection not found"
        )

    logger.info(f"Return selection '{identifier}' (username={username}) from db")
    await redis_client.set(cache_key, selection.model_dump_json(), ex=300)
    return selection


@router.post(
    "/", response_model=BookSelectionSchema, status_code=status.HTTP_201_CREATED
)
async def create_book_selection(
    data: BookSelectionCreate,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    new_selection = await crud.create_book_selection(session, data)
    logger.info(f"Created book selection with data {data}")
    await redis_client.delete("selections:all*")
    return new_selection


@router.post("/upload-cover")
async def upload_selection_cover(file: UploadFile = File(...)):
    logger.info(f"Upload selection cover: {file}")
    allowed_types = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}

    if file.content_type not in allowed_types:
        logger.error(f"Unsupported file type: {file.content_type}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Допустимі тільки JPG, PNG, та WEBP",
        )

    content = await file.read()

    if len(content) > MAX_COVER_SIZE:
        logger.error(f"File size exceeds limit")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Максимальний розмір файлу - 5 МБ",
        )

    extension = allowed_types[file.content_type]
    filename = f"{uuid4().hex}{extension}"
    file_path = MEDIA_DIR / filename
    file_path.write_bytes(content)

    return {"cover_image": f"/media/book_selections/{filename}"}


@router.patch("/{selection_id}", response_model=BookSelectionSchema)
async def update_book_selection(
    selection_id: int,
    data: BookSelectionUpdatePartial,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    updated_selection = await crud.update_book_selection(
        session=session, selection_id=selection_id, data=data, partial=True
    )

    await redis_client.delete(f"selection:{selection_id}")
    await redis_client.delete(f"selection:{updated_selection.slug}")
    await redis_client.delete("selections:all*")

    return updated_selection


@router.delete("/{selection_id}", status_code=status.HTTP_200_OK)
async def delete_book_selection(
    selection_id: int,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    success = await crud.delete_book_selection(session, selection_id)

    if not success:
        logger.error(f"Failed to delete book selection {selection_id} - Not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Book selection not found"
        )

    await redis_client.delete(f"selection:{selection_id}")
    await redis_client.delete("selections:all*")

    return {"ok": True}
