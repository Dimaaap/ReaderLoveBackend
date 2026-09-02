import json
import io
from pathlib import Path
from uuid import uuid4
from typing import Optional

from loguru import logger
from fastapi import APIRouter, Depends, HTTPException, status, Query, File, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core.redis_config import redis_client
from core.models import db_helper
from entities.books.schema import (
    BookSchema,
    BookCreate,
    BookUpdatePartial,
    BookDetailSchema,
    BookSchemaWithSessions,
    ExportLibraryOptions,
    UserBookStatusUpdate,
    UserBookSchema,
)

from . import crud
from . import utils

router = APIRouter(tags=["Books"])
MEDIA_DIR = Path("media/books")
MEDIA_DIR.mkdir(parents=True, exist_ok=True)
MAX_COVER_SIZE = 5 * 1024 * 1024


@router.get("/")
async def get_all_books(
    search: Optional[str] = Query(None),
    limit: int | None = Query(default=None, ge=1, le=100),
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    normalized_search = search.strip().lower() if search else ""

    cache_key = (
        f"books:all:search:{normalized_search}:limit:{limit}"
        if normalized_search
        else f"books:all:limit:{limit}"
    )

    cached = await redis_client.get(cache_key)
    if cached:
        logger.info(
            f"Get all books with search query {normalized_search} and limit {limit} from Redis cache"
        )
        return json.loads(cached)

    books = await crud.get_all_books(
        session=session, limit=limit, search=normalized_search
    )
    result = [BookSchema.model_validate(book) for book in books]

    logger.info(
        f"Return all books with search query {normalized_search} and limit {limit} from db"
    )

    await redis_client.set(
        cache_key, json.dumps([b.model_dump() for b in result]), ex=600
    )
    return result


@router.get("/{book_id}", response_model=BookSchema)
async def get_book_by_id(
    book_id: int,
    username: str,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    cache_key = f"books:{book_id}:user:{username}"

    cached = await redis_client.get(cache_key)
    if cached:
        logger.info(f"Get book with id {book_id} for user {username} from Redis cache")
        return json.loads(cached)

    book = await crud.get_book_by_id(session, book_id, username)
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Book not found"
        )
    result = BookSchema.model_validate(book)
    logger.info(f"Return book with id {book_id} for user {username} from db")
    await redis_client.set(cache_key, result.model_dump_json(), ex=300)
    return result


@router.get("/by-slug/{book_slug}", response_model=BookSchema)
async def get_book_by_slug(
    book_slug: str, session: AsyncSession = Depends(db_helper.scoped_session_dependency)
):
    cache_key = f"books:{book_slug}"

    cached = await redis_client.get(cache_key)

    if cached:
        logger.info(f"Get book with slug {book_slug} from Redis cache")
        return json.loads(cached)

    book = await crud.get_book_by_slug(session, book_slug)
    if not book:
        logger.error(f"Failed to get book {book_slug} - Book was not found in db")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Book not found"
        )

    result = BookSchema.model_validate(book)
    logger.info(f"Return book {book_slug} from db")
    await redis_client.set(cache_key, result.model_dump_json(), ex=300)
    return result


@router.get("/by-slug/{book_slug}/{username}", response_model=UserBookSchema)
async def get_book_by_slug_for_user(
    book_slug: str,
    username: str,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    cache_key = f"book:{username}:{book_slug}"

    cached = await redis_client.get(cache_key)

    if cached:
        logger.info(f"Get book {book_slug} for user {username} from Redis cache")
        return json.loads(cached)

    book_data = await crud.get_book_by_slug_for_user_with_status(
        session, book_slug, username
    )

    if not book_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Book not found"
        )

    result = UserBookSchema.model_validate(book_data)
    logger.info(f"Return book {book_slug} for user {username} from db")
    await redis_client.set(cache_key, result.model_dump_json(), ex=600)

    return result


@router.delete("/status/{book_slug}/{username}", status_code=status.HTTP_200_OK)
async def delete_user_book_status(
    book_slug: str,
    username: str,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    deleted = await crud.delete_user_book_status(session, username, book_slug)

    if not deleted:
        logger.error(
            f"Failed to delete reading book status in book "
            f"{book_slug} for user {username} - book was not found in db"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Book not found"
        )

    cache_key = f"book:{username}:{book_slug}"
    await redis_client.delete(cache_key)
    await redis_client.delete(f"books:{username}:active")
    return {"status": "ok"}


@router.get("/{username}/slug/{book_slug}", response_model=BookDetailSchema)
async def get_book_details(
    username: str,
    book_slug: str,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    book_details = await crud.get_book_by_slug_for_user(session, book_slug, username)

    if not book_details:
        logger.error(f"Failed to get book {book_slug} for user {username}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Book with slug {book_slug} was not found",
        )

    return book_details


@router.get("/current-reading/{username}", response_model=BookSchemaWithSessions)
async def get_current_reading_book(
    username: str,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
    limit: int = 5,
):
    book_data = await crud.get_current_main_reading_book(session, username, limit)

    if not book_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Last reading book for user {username} was not found",
        )

    return book_data


@router.get(
    "/book-with-sessions/{book_slug}/{username}", response_model=BookSchemaWithSessions
)
async def get_book_with_sessions(
    book_slug: str,
    username: str,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    book_data = await crud.get_book_by_slug_for_user_with_sessions_stats(
        session, book_slug, username
    )

    if not book_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Not found books"
        )

    return book_data


@router.post("/", response_model=BookSchema, status_code=status.HTTP_201_CREATED)
async def create_book(
    data: BookCreate,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    new_book = await crud.create_book(session, data)
    logger.info(f"Created book with data {data}")
    await redis_client.delete("books:all")
    return new_book


@router.post("/upload-cover")
async def upload_book_cover(file: UploadFile = File(...)):
    logger.info(f"Upload book cover: {file.filename}")
    allowed_types = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
    }

    if file.content_type not in allowed_types:
        logger.error(f"Unsupported file type: {file.content_type}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Допустимі тільки JPG, PNG, та WEBP",
        )

    content = await file.read()

    if len(content) > MAX_COVER_SIZE:
        logger.error(f"File is too much")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Максимальний розмір файлу - 5 МБ",
        )

    extension = allowed_types[file.content_type]
    filename = f"{uuid4().hex}{extension}"
    file_path = MEDIA_DIR / filename
    file_path.write_bytes(content)

    return {"image_link": f"/media/books/{filename}"}


@router.post("/{username}/status/{book_slug}")
async def update_or_add_book_status(
    username: str,
    book_slug: str,
    data: UserBookStatusUpdate,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    try:
        assoc = await crud.set_user_book_status(session, username, book_slug, data)
    except ValueError as e:
        logger.error(
            f"Failed to set reading status in book {book_slug} for user {username} with data {data}"
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    await redis_client.delete(f"books:{username}:active")
    await redis_client.delete(f"book:{username}:{book_slug}")
    await redis_client.delete(f"books:{book_slug}")

    return {
        "ok": True,
        "book_slug": book_slug,
        "status": (
            assoc.status.value if hasattr(assoc.status, "value") else str(assoc.status)
        ),
        "last_read_page": assoc.last_read_page,
    }


@router.patch("/{book_id}", response_model=BookSchema)
async def update_book(
    book_id: int,
    data: BookUpdatePartial,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    book = await crud.get_book_by_id(session, book_id)

    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Book not found"
        )
    updated_book = await crud.update_book(session, book, data, partial=True)

    await redis_client.delete(f"books:{book_id}")
    await redis_client.delete("books:all")
    return updated_book


@router.get("/{username}/books")
async def get_user_active_books(
    username: str, session: AsyncSession = Depends(db_helper.scoped_session_dependency)
):
    cache_key = f"books:{username}:active"

    cached = await redis_client.get(cache_key)

    if cached:
        return json.loads(cached)

    books = await crud.get_user_active_books_for_notes(username, session)
    await redis_client.set(
        cache_key, json.dumps([b.model_dump() for b in books]), ex=600
    )
    return books


@router.post("/{username}/export")
async def export_user_library(
    username: str,
    options: ExportLibraryOptions,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    data = await crud.get_user_library_for_export(
        session, username, options.filter_status, options.include_notes
    )

    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Не знайдено книг за обраними критеріями для експорту",
        )

    file_bytes = None
    media_type = None
    filename = None

    if options.format == "csv":
        file_bytes = utils.generate_csv_export(data, options.include_notes)
        media_type = "text/csv"
        filename = f"{username}_library.csv"

    elif options.format == "json":
        file_bytes = utils.generate_json_export(data)
        media_type = "application/json"
        filename = f"{username}_library.json"

    elif options.format == "pdf":
        file_bytes = utils.generate_pdf_export(data)
        media_type = "application/pdf"
        filename = f"{username}_library.pdf"

    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment: filename="{filename}"'},
    )


@router.delete("/{book_id}")
async def delete_book_view(
    book_id: int,
    username: str,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    book = await crud.get_book_by_id_without_username(session, book_id)

    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Book not found"
        )
    await crud.delete_book(session, book)
    await redis_client.delete(f"books:{book_id}")
    await redis_client.delete("books:all")

    return {"ok": True}
