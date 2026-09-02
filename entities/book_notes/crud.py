from fastapi import HTTPException, status

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from core.models import BookNotes, User
from entities.book_notes.schema import (
    BookNotesSchema,
    BookNotesCreate,
    BookNotesUpdate,
    BookNotesUpdatePartial,
)


async def get_all_book_notes(session: AsyncSession) -> list[BookNotesSchema]:
    logger.info("Get all book notes")
    statement = (
        select(BookNotes)
        .options(joinedload(BookNotes.book), joinedload(BookNotes.user))
        .order_by(BookNotes.id)
    )

    result = await session.execute(statement)

    book_notes = result.scalars().all()
    return [BookNotesSchema.model_validate(note) for note in book_notes]


async def get_user_notes(
    username: str, session: AsyncSession, limit: int = None
) -> list[BookNotesSchema]:
    logger.info(f"Try to get all user notes for user {username} with limit {limit}")

    statement = (
        select(BookNotes)
        .join(BookNotes.user)
        .where(User.username == username)
        .options(joinedload(BookNotes.book), joinedload(BookNotes.user))
        .order_by(BookNotes.created_at.desc())
    )

    if limit is not None:
        logger.info(f"limit={limit}")
        statement = statement.limit(limit)

    result = await session.execute(statement)
    book_notes = result.scalars().all()

    return [BookNotesSchema.model_validate(note) for note in book_notes]


async def get_user_book_notes(
    username: str, book_id: int, session: AsyncSession
) -> list[BookNotesSchema]:
    logger.info(f"Try to get all book notes for username {username} and book {book_id}")
    statement = (
        select(BookNotes)
        .join(BookNotes.user)
        .where(User.username == username, BookNotes.book_id == book_id)
        .options(joinedload(BookNotes.book), joinedload(BookNotes.user))
        .order_by(BookNotes.created_at.desc())
    )

    result = await session.execute(statement)
    book_notes = result.scalars().all()

    return [BookNotesSchema.model_validate(note) for note in book_notes]


async def toggle_book_note_importance(
    session: AsyncSession, note_id: int
) -> BookNotes | None:
    logger.info(f"Try to toggle importance for book note {note_id}")
    statement = (
        select(BookNotes)
        .where(BookNotes.id == note_id)
        .options(joinedload(BookNotes.book), joinedload(BookNotes.user))
    )

    result = await session.execute(statement)
    book_note = result.scalar_one_or_none()

    if book_note is None:
        logger.error(
            f"Failed to toggle importance for book note {note_id} - book note was not found"
        )
        return None

    book_note.is_important = not getattr(book_note, "is_important", False)
    await session.commit()
    await session.refresh(book_note)
    return book_note


async def get_book_note_by_id(
    session: AsyncSession, note_id: int
) -> BookNotesSchema | None:

    logger.info(f"Try to get book note with id {note_id}")
    statement = (
        select(BookNotes)
        .where(BookNotes.id == note_id)
        .options(joinedload(BookNotes.book), joinedload(BookNotes.user))
    )

    result = await session.execute(statement)
    return result.scalar_one_or_none()


async def create_book_note(session: AsyncSession, data: BookNotesCreate) -> BookNotes:
    logger.info(
        f"Try to create book note for user {data.user_username}, data {data.note_text}"
    )
    user_data = await session.execute(
        select(User).where(User.username == data.user_username)
    )
    user = user_data.scalar_one_or_none()

    if not user:
        logger.error(
            f"Failed to create book note for user {data.user_username} - USER WAS NOT FOUND"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="user not found"
        )

    book_note_data = data.model_dump(exclude={"user", "book", "user_username"})
    book_note = BookNotes(**book_note_data, user_id=user.id)

    session.add(book_note)
    await session.commit()
    await session.refresh(book_note, ["user", "book"])
    return book_note


async def update_book_note(
    session: AsyncSession,
    book_note_id: int,
    book_note_update: BookNotesUpdate | BookNotesUpdatePartial,
    partial: bool = False,
) -> BookNotes:

    logger.info(f"Try to update book note {book_note_id} with data {book_note_update}")
    book_note_sql = await session.execute(
        select(BookNotes).where(BookNotes.id == book_note_id)
    )

    book_note = book_note_sql.scalar_one_or_none()

    update_data = book_note_update.model_dump(exclude_unset=partial)

    for key, value in update_data.items():
        setattr(book_note, key, value)

    await session.commit()
    await session.refresh(book_note)
    return book_note


async def delete_book_note(session: AsyncSession, note_id: int) -> (bool, BookNotes):
    logger.info(f"Try to delete book note with id {note_id}")
    result = await session.execute(
        select(BookNotes)
        .where(BookNotes.id == note_id)
        .options(joinedload(BookNotes.user))
    )
    book_note = result.scalar_one_or_none()
    deleted_note = book_note

    if book_note is None:
        logger.error(
            f"Failed to delete book note with id {note_id} - book note was not found"
        )
        return False, None

    await session.delete(book_note)
    await session.commit()
    return True, deleted_note
