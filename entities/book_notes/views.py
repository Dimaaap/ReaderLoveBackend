import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.redis_config import redis_client
from core.models import db_helper
from entities.book_notes.schema import (
    BookNotesCreate,
    BookNotesSchema,
    BookNotesUpdatePartial,
)

from . import crud

router = APIRouter(tags=["Book Notes"])


@router.get("/", response_model=list[BookNotesSchema])
async def get_all_book_notes(
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    cache_key = "book_notes:all"
    cached = await redis_client.get(cache_key)

    if cached:
        return json.loads(cached)

    data = await crud.get_all_book_notes(session)
    serialized_data = json.dumps([item.model_dump(mode="json") for item in data])

    await redis_client.set(cache_key, serialized_data, ex=300)
    return data


@router.post("/", response_model=BookNotesSchema, status_code=201)
async def create_book_note_view(
    data: BookNotesCreate,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    book_note = await crud.create_book_note(session, data)

    await redis_client.delete("book_notes:all")
    user_cache_key = f"book_notes:user:{data.user_username}"
    await redis_client.delete(user_cache_key)
    return book_note


@router.get("/by-username", response_model=list[BookNotesSchema])
async def get_book_notes_by_username(
    username: str,
    limit: int,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    cache_key = f"book_notes:user:{username}"
    cached = await redis_client.get(cache_key)

    if cached:
        return json.loads(cached)[:limit]

    data = await crud.get_user_notes(username, session, limit)
    serialized_data = json.dumps([item.model_dump(mode="json") for item in data])

    await redis_client.set(cache_key, serialized_data, ex=300)
    return data


@router.get("/by-user-book", response_model=list[BookNotesSchema])
async def get_user_book_notes(
    username: str,
    book_id: int,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    cache_key = f"book_notes:user:{username}:book:{book_id}"
    cached = await redis_client.get(cache_key)

    if cached:
        return json.loads(cached)

    data = await crud.get_user_book_notes(username, book_id, session)

    serialized_data = json.dumps([item.model_dump(mode="json") for item in data])
    await redis_client.set(cache_key, serialized_data, ex=300)
    return data


@router.get("/{note_id}", response_model=BookNotesSchema)
async def get_book_note_by_id(
    note_id: int, session: AsyncSession = Depends(db_helper.scoped_session_dependency)
):
    cache_key = f"book_notes:{note_id}"
    cached = await redis_client.get(cache_key)

    if cached:
        return json.loads(cached)

    db_note = await crud.get_book_note_by_id(session, note_id)

    if not db_note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Book note not found"
        )

    result = BookNotesSchema.model_validate(db_note)
    await redis_client.set(cache_key, result.model_dump_json(), ex=300)
    return result


@router.patch("/{note_id}/toggle-importance", response_model=BookNotesSchema)
async def toggle_book_notes_importance(
    note_id: int, session: AsyncSession = Depends(db_helper.scoped_session_dependency)
):
    updated_note = await crud.toggle_book_note_importance(session, note_id)

    if updated_note is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Book Note is not found"
        )
    result = BookNotesSchema.model_validate(updated_note)

    try:
        await redis_client.delete(f"book_notes:{note_id}")

        await redis_client.delete(f"book_notes:all")

        if updated_note.user:
            await redis_client.delete(f"book_notes:user:{updated_note.user.username}")
            await redis_client.delete(
                f"book_notes:user:{updated_note.user.username}:book:{updated_note.book_id}"
            )
    except Exception:
        pass
    return result


@router.patch("/{book_note_id}", response_model=BookNotesSchema)
async def update_book_note(
    book_note_id: int,
    data: BookNotesUpdatePartial,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    book_note = await crud.get_book_note_by_id(session, book_note_id)

    if not book_note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Book note not found"
        )

    updated_note = await crud.update_book_note(
        session, book_note.id, data, partial=True
    )

    try:
        await redis_client.delete(f"book_notes:{book_note_id}")

        await redis_client.delete(f"book_notes:all")

        if updated_note.user:
            await redis_client.delete(f"book_notes:user:{updated_note.user.username}")
            await redis_client.delete(
                f"book_notes:user:{updated_note.user.username}:book:{updated_note.book_id}"
            )
    except Exception:
        pass
    return updated_note


@router.delete("/{note_id}")
async def delete_book_note_by_id(
    note_id: int, session: AsyncSession = Depends(db_helper.scoped_session_dependency)
):
    is_deleted, deleted_note = await crud.delete_book_note(session, note_id)

    if is_deleted:
        try:
            await redis_client.delete(f"book_notes:{note_id}")

            await redis_client.delete(f"book_notes:all")

            if deleted_note.user:
                await redis_client.delete(
                    f"book_notes:user:{deleted_note.user.username}"
                )
                await redis_client.delete(
                    f"book_notes:user:{deleted_note.user.username}:book:{deleted_note.book_id}"
                )
        except Exception:
            pass
