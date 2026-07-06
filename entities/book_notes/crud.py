from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, AsyncSessionTransaction
from sqlalchemy.orm import joinedload

from core.models import BookNotes, User
from entities.book_notes.schema import (
    BookNotesSchema,
    BookNotesCreate,
    BookNotesUpdate,
    BookNotesUpdatePartial,
)


async def get_all_book_notes(session: AsyncSession) -> list[BookNotesSchema]:
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
    statement = (
        select(BookNotes)
        .join(BookNotes.user)
        .where(User.username == username)
        .options(joinedload(BookNotes.book), joinedload(BookNotes.user))
        .order_by(BookNotes.created_at.desc())
    )

    if limit is not None:
        statement = statement.limit(limit)

    result = await session.execute(statement)
    book_notes = result.scalars().all()

    return [BookNotesSchema.model_validate(note) for note in book_notes]


async def get_user_book_notes(
    username: str, book_id: int, session: AsyncSession
) -> list[BookNotesSchema]:

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
    statement = (
        select(BookNotes)
        .where(BookNotes.id == note_id)
        .options(joinedload(BookNotes.book), joinedload(BookNotes.user))
    )

    result = await session.execute(statement)
    book_note = result.scalar_one_or_none()

    if book_note is None:
        return None

    book_note.is_important = not getattr(book_note, "is_important", False)
    await session.commit()
    await session.refresh(book_note)
    return book_note


async def get_book_note_by_id(
    session: AsyncSession, note_id: int
) -> BookNotesSchema | None:
    statement = (
        select(BookNotes)
        .where(BookNotes.id == note_id)
        .options(joinedload(BookNotes.book), joinedload(BookNotes.user))
    )

    result = await session.execute(statement)
    return result.scalar_one_or_none()


async def create_book_note(session: AsyncSession, data: BookNotesCreate) -> BookNotes:
    book_note_data = data.model_dump(exclude={"user", "book"})
    book_note = BookNotes(**book_note_data)

    session.add(book_note)
    await session.commit()
    await session.refresh(book_note)
    return book_note


async def update_book_note(
    session: AsyncSession,
    book_note: BookNotes,
    book_note_update: BookNotesUpdate | BookNotesUpdatePartial,
    partial: bool = False,
) -> BookNotes:
    update_data = book_note_update.model_dump(exclude_unset=partial)

    for key, value in update_data.items():
        setattr(book_note, key, value)

    await session.commit()
    await session.refresh(book_note)
    return book_note


async def delete_book_note(session: AsyncSession, note_id: int) -> bool:
    result = await session.execute(select(BookNotes).where(BookNotes.id == note_id))
    book_note = result.scalar_one_or_none()

    if book_note is None:
        return False

    await session.delete(book_note)
    await session.commit()
    return True
