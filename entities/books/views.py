import json
import io
from fastapi import APIRouter, Depends, HTTPException, status
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
)

from . import crud
from . import utils

router = APIRouter(tags=["Books"])


@router.get("/")
async def get_all_books(
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    cache_key = "books:all"

    cached = await redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    books = await crud.get_all_books(session)
    result = [BookSchema.model_validate(book) for book in books]

    await redis_client.set(
        cache_key, json.dumps([b.model_dump() for b in result]), ex=600
    )
    return result


@router.get("/{book_id}", response_model=BookSchema)
async def get_book_by_id(
    book_id: int, session: AsyncSession = Depends(db_helper.scoped_session_dependency)
):
    cache_key = f"books:{book_id}"

    cached = await redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    book = await crud.get_book_by_id(session, book_id)
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Book not found"
        )
    result = BookSchema.model_validate(book)
    await redis_client.set(cache_key, result.model_dump_json(), ex=300)
    return result


@router.get("/by-slug/{book_slug}", response_model=BookSchema)
async def get_book_by_slug(
    book_slug: str, session: AsyncSession = Depends(db_helper.scoped_session_dependency)
):
    cache_key = f"books:{book_slug}"

    cached = await redis_client.get(cache_key)

    if cached:
        return json.loads(cached)

    book = await crud.get_book_by_slug(session, book_slug)
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Book not found"
        )

    result = BookSchema.model_validate(book)
    await redis_client.set(cache_key, result.model_dump_json(), ex=300)
    return result


@router.get("/{username}/slug/{book_slug}", response_model=BookDetailSchema)
async def get_book_details(
    username: str,
    book_slug: str,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    book_details = await crud.get_book_by_slug_for_user(session, book_slug, username)

    if not book_details:
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
    await redis_client.delete("books:all")
    return new_book


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
    book_id: int, session: AsyncSession = Depends(db_helper.scoped_session_dependency)
):
    book = await crud.get_book_by_id(session, book_id)

    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Book not found"
        )
    await crud.delete_book(session, book)
    await redis_client.delete(f"books:{book_id}")
    await redis_client.delete("books:all")

    return {"ok": True}
