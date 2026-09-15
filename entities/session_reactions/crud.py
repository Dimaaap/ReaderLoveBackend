from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from core.models import Book, ReadingSession, SessionReaction, User
from entities.reading_sessions.schema import (
    BookInSessionSchema,
    ReadingSessionSchema,
    UserInSessionSchema,
)


def map_session_to_schema(
    db_session: ReadingSession, current_user_id: str | int | None = None
) -> ReadingSessionSchema:
    reactions_count = {}
    user_reactions = []

    db_reactions = getattr(db_session, "reactions", []) or []
    for reaction in db_reactions:
        reactions_count[reaction.emoji] = reactions_count.get(reaction.emoji, 0) + 1

        if current_user_id is not None and str(reaction.user_id) == str(
            current_user_id
        ):
            user_reactions.append(reaction.emoji)

    book_schema = BookInSessionSchema.model_validate(db_session.book)
    user_schema = UserInSessionSchema.model_validate(db_session.user)

    return ReadingSessionSchema(
        id=db_session.id,
        user_id=str(db_session.user_id),
        book_id=db_session.book_id,
        start_page=db_session.start_page,
        end_page=db_session.end_page,
        is_tracked=db_session.is_tracked,
        comment=db_session.comment,
        started_at=db_session.started_at,
        ended_at=db_session.ended_at,
        user=user_schema,
        book=book_schema,
        reactions=reactions_count,
        user_reactions=user_reactions,
    )


async def toggle_session_reaction(
    session: AsyncSession, session_id: int, user_id: int | str, emoji: str
) -> str:
    statement = select(SessionReaction).where(
        SessionReaction.session_id == session_id,
        SessionReaction.user_id == user_id,
        SessionReaction.emoji == emoji,
    )

    result = await session.execute(statement)
    existing_reaction = result.scalar_one_or_none()

    if existing_reaction:
        await session.delete(existing_reaction)
        await session.commit()
        return "removed"

    new_reaction = SessionReaction(session_id=session_id, user_id=user_id, emoji=emoji)
    session.add(new_reaction)
    await session.commit()
    return "added"


async def get_reading_session_by_id(
    session: AsyncSession, session_id: int
) -> ReadingSession | None:
    statement = (
        select(ReadingSession)
        .where(ReadingSession.id == session_id)
        .options(
            joinedload(ReadingSession.user),
            joinedload(ReadingSession.book).selectinload(Book.authors),
            selectinload(ReadingSession.reactions),
        )
    )

    result = await session.execute(statement)
    return result.unique().scalar_one_or_none()


async def get_all_reading_sessions(
    session: AsyncSession, current_user_id: str | int | None = None
) -> list[ReadingSessionSchema]:
    statement = (
        select(ReadingSession)
        .options(
            joinedload(ReadingSession.user),
            joinedload(ReadingSession.book).selectinload(Book.authors),
            selectinload(ReadingSession.reactions),
        )
        .order_by(ReadingSession.id.desc())
    )

    result = await session.execute(statement)
    sessions = result.unique().scalars().all()

    return [map_session_to_schema(s, current_user_id) for s in sessions]


async def get_user_reading_session(
    username: str,
    session: AsyncSession,
    limit: int,
    current_user_id: str | int | None = None,
) -> list[ReadingSessionSchema]:
    statement = (
        select(ReadingSession)
        .join(User, ReadingSession.user_id == User.id)
        .where(User.username == username)
        .options(
            joinedload(ReadingSession.user),
            joinedload(ReadingSession.book).selectinload(Book.authors),
            selectinload(ReadingSession.reactions),
        )
        .order_by(ReadingSession.id.desc())
        .limit(limit)
    )

    result = await session.execute(statement)
    sessions = result.unique().scalars().all()

    return [map_session_to_schema(s, current_user_id) for s in sessions]


async def get_user_book_reading_session(
    username: str,
    book_id: int,
    session: AsyncSession,
    current_user_id: str | int | None = None,
) -> list[ReadingSessionSchema]:
    statement = (
        select(ReadingSession)
        .join(User, ReadingSession.user_id == User.id)
        .where(User.username == username, ReadingSession.book_id == book_id)
        .options(
            joinedload(ReadingSession.user),
            joinedload(ReadingSession.book).selectinload(Book.authors),
            selectinload(ReadingSession.reactions),
        )
        .order_by(ReadingSession.id.desc())
    )

    result = await session.execute(statement)
    sessions = result.unique().scalars().all()

    return [map_session_to_schema(s, current_user_id) for s in sessions]
