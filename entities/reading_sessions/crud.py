from fastapi import HTTPException, status
from datetime import datetime
import calendar

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from core.models import ReadingSession, User, UserBookAssociation, Book, SessionReaction
from core.models.user_book_association import BookReadStatus
from entities.reading_sessions.schema import (
    ReadingSessionSchema,
    ReadingSessionCreate,
    ReadingSessionUpdate,
    ReadingSessionUpdatePartial,
    BookInSessionSchema,
    UserInSessionSchema,
)


def map_session_to_schema(
    db_session: ReadingSession, current_user_id: str | None = None
) -> ReadingSessionSchema:
    reactions_count: dict[str, int] = {}
    user_reactions: list[str] = []

    db_reactions = getattr(db_session, "reactions", []) or []
    for r in db_reactions:
        reactions_count[r.emoji] = reactions_count.get(r.emoji, 0) + 1
        if current_user_id and str(r.user_id) == str(current_user_id):
            user_reactions.append(r.emoji)

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


async def get_all_reading_sessions(
    session: AsyncSession, current_user_id: str | None = None
) -> list[ReadingSessionSchema]:
    logger.info("Try to get all reading sessions")
    statement = (
        select(ReadingSession)
        .options(
            joinedload(ReadingSession.user),
            joinedload(ReadingSession.book).selectinload(Book.authors),
            selectinload(ReadingSession.reactions),
        )
        .order_by(ReadingSession.started_at.desc())
    )

    result = await session.execute(statement)
    reading_sessions = result.scalars().unique().all()

    return [map_session_to_schema(s, current_user_id) for s in reading_sessions]


async def get_user_reading_session(
    username: str,
    session: AsyncSession,
    limit: int = None,
    current_user_id: str | None = None,
) -> list[ReadingSessionSchema]:
    logger.info(
        f"Try to get all reading sessions for user {username} with limit {limit}"
    )
    statement = (
        select(ReadingSession)
        .join(ReadingSession.user)
        .where(User.username == username)
        .options(
            joinedload(ReadingSession.user),
            joinedload(ReadingSession.book).selectinload(Book.authors),
            selectinload(ReadingSession.reactions),
        )
        .order_by(ReadingSession.started_at.desc())
    )

    if limit is not None:
        statement = statement.limit(limit)

    result = await session.execute(statement)
    reading_sessions = result.scalars().unique().all()

    return [map_session_to_schema(s, current_user_id) for s in reading_sessions]


async def get_user_book_reading_session(
    username: str,
    book_id: int,
    session: AsyncSession,
    current_user_id: str | None = None,
) -> list[ReadingSessionSchema]:

    logger.info(
        f"Try to get all reading sessions for user {username} and book {book_id}"
    )
    statement = (
        select(ReadingSession)
        .join(ReadingSession.user)
        .where(
            User.username == username,
            ReadingSession.book_id == book_id,
        )
        .options(
            joinedload(ReadingSession.user),
            joinedload(ReadingSession.book).selectinload(Book.authors),
            selectinload(ReadingSession.reactions),
        )
        .order_by(ReadingSession.started_at.desc())
    )

    result = await session.execute(statement)
    reading_sessions = result.scalars().unique().all()

    return [map_session_to_schema(s, current_user_id) for s in reading_sessions]


async def get_reading_session_by_id(
    session: AsyncSession, session_id: int
) -> ReadingSession | None:
    logger.info(f"Try to get reading session with id {session_id}")
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
    return result.scalar_one_or_none()


async def create_reading_session(
    session: AsyncSession, data: ReadingSessionCreate
) -> ReadingSession:

    logger.info(f"Try to create new reading session with data {data}")
    user = select(User).where(User.username == data.username)
    result = await session.execute(user)
    user_db = result.scalar_one_or_none()

    if not user_db:
        logger.error(
            f"Failed to get user with username {data.username} - user was not found in db"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"user with username {data.username} was not found",
        )

    association_statement = (
        select(UserBookAssociation)
        .options(selectinload(UserBookAssociation.book))
        .where(
            UserBookAssociation.user_id == user_db.id,
            UserBookAssociation.book_id == data.book_id,
        )
    )
    association_result = await session.execute(association_statement)
    association = association_result.scalar_one_or_none()

    current_page = data.end_page if data.end_page is not None else data.start_page

    if association:
        logger.info(f"Reading session for user {user_db.username} already exists")
        if (
            association.status != BookReadStatus.READING
            and association.status != BookReadStatus.FINISHED
        ):
            association.status = BookReadStatus.READING

        if current_page > association.last_read_page:
            logger.info(f"Set new current page {association.last_read_page}")
            association.last_read_page = current_page

            if association.book and current_page >= association.book.pages_count:
                logger.info("Set book status as finished")
                association.status = BookReadStatus.FINISHED

    else:
        logger.info("Create new reading session")
        association = UserBookAssociation(
            user_id=user_db.id,
            book_id=data.book_id,
            status=BookReadStatus.READING,
            last_read_page=current_page,
        )
        session.add(association)

    reading_session_data = data.model_dump(exclude={"user", "book", "username"})
    reading_session_data["user_id"] = user_db.id
    reading_session = ReadingSession(**reading_session_data)

    session.add(reading_session)
    await session.commit()
    await session.refresh(reading_session, ["user", "book"])
    return reading_session


async def update_reading_session(
    session: AsyncSession,
    reading_session: ReadingSession,
    reading_session_update: ReadingSessionUpdate | ReadingSessionUpdatePartial,
    partial: bool = False,
) -> ReadingSession:
    logger.info(f"Try to update reading session with data: {reading_session_update}")
    update_data = reading_session_update.model_dump(exclude_unset=partial)

    for key, value in update_data.items():
        setattr(reading_session, key, value)

    target_page = (
        reading_session.end_page
        if reading_session.end_page is not None
        else reading_session.start_page
    )

    if target_page is not None:
        assoc_stmt = (
            select(UserBookAssociation)
            .options(selectinload(UserBookAssociation.book))
            .where(
                UserBookAssociation.user_id == reading_session.user_id,
                UserBookAssociation.book_id == reading_session.book_id,
            )
        )
        assoc_result = await session.execute(assoc_stmt)
        association = assoc_result.scalar_one_or_none()

        if association:
            if target_page > association.last_read_page:
                association.last_read_page = target_page

            if association.book and target_page >= association.book.pages_count:
                association.status = BookReadStatus.FINISHED

    await session.commit()
    await session.refresh(reading_session)

    return reading_session


async def delete_reading_session(session: AsyncSession, session_id: int) -> bool:
    result = await session.execute(
        select(ReadingSession).where(ReadingSession.id == session_id)
    )
    reading_session = result.scalar_one_or_none()

    if reading_session is None:
        return False

    user_id = reading_session.user_id
    book_id = reading_session.book_id

    await session.delete(reading_session)
    await session.flush()

    max_page_stmt = (
        select(ReadingSession.end_page)
        .where(
            ReadingSession.user_id == user_id,
            ReadingSession.book_id == book_id,
            ReadingSession.end_page.isnot(None),
        )
        .order_by(ReadingSession.end_page.desc())
        .limit(1)
    )
    max_page_result = await session.execute(max_page_stmt)
    new_max_page = max_page_result.scalar_one_or_none() or 0

    assoc_stmt = select(UserBookAssociation).where(
        UserBookAssociation.user_id == user_id,
        UserBookAssociation.book_id == book_id,
    )
    assoc_result = await session.execute(assoc_stmt)
    association = assoc_result.scalar_one_or_none()

    if association:
        association.last_read_page = new_max_page

    await session.commit()
    return True


async def toggle_session_reaction(
    session: AsyncSession, session_id: int, user_id: str, emoji: str
) -> str:
    stmt = select(SessionReaction).where(
        SessionReaction.session_id == session_id,
        SessionReaction.user_id == user_id,
        SessionReaction.emoji == emoji,
    )
    result = await session.execute(stmt)
    existing_reaction = result.scalar_one_or_none()

    if existing_reaction:
        await session.delete(existing_reaction)
        await session.commit()
        return "removed"
    else:
        new_reaction = SessionReaction(
            session_id=session_id, user_id=user_id, emoji=emoji
        )
        session.add(new_reaction)
        await session.commit()
        return "added"


async def get_user_monthly_reading_sessions(
    username: str, year: int, month: int, session: AsyncSession
) -> list[ReadingSessionSchema]:
    logger.info(f"Try to get reading sessions for user {username} for {year}-{month}")

    _, last_day = calendar.monthrange(year, month)
    start_date = datetime(year, month, 1, 0, 0, 0)
    end_date = datetime(year, month, last_day, 23, 59, 59)

    statement = (
        select(ReadingSession)
        .join(ReadingSession.user)
        .where(
            User.username == username,
            ReadingSession.started_at >= start_date,
            ReadingSession.started_at <= end_date,
        )
        .options(
            joinedload(ReadingSession.user),
            joinedload(ReadingSession.book).selectinload(Book.authors),
            selectinload(ReadingSession.reactions),
        )
        .order_by(ReadingSession.started_at.asc())
    )

    result = await session.execute(statement)
    reading_sessions = result.scalars().unique().all()

    return [map_session_to_schema(s) for s in reading_sessions]
