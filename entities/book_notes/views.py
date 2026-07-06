import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.redis_config import redis_client
from core.models import db_helper
from entities.book_notes.schema import BookNotesCreate, BookNotesSchema

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


@router.delete("/{note_id}")
async def delete_book_note_by_id(
    note_id: int, session: AsyncSession = Depends(db_helper.scoped_session_dependency)
):
    deleted = await crud.delete_book_note(session, note_id)

    if deleted:
        try:
            await redis_client.delete(f"reading_sessions:all")
            await redis_client.delete(f"reading_sessions:{note_id}")
        except Exception:
            return
