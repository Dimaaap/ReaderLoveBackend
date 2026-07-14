from fastapi import HTTPException, status

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from core.models import ReadingSession, User, UserBookAssociation
from core.models.user_book_association import BookReadStatus
from entities.reading_sessions.schema import (
    ReadingSessionSchema,
    ReadingSessionCreate,
    ReadingSessionUpdate,
    ReadingSessionUpdatePartial,
)


async def get_all_reading_sessions(session: AsyncSession) -> list[ReadingSessionSchema]:
    statement = (
        select(ReadingSession)
        .options(
            joinedload(ReadingSession.book),
            joinedload(ReadingSession.user),
        )
        .order_by(ReadingSession.id)
    )

    result = await session.execute(statement)

    reading_sessions = result.scalars().all()
    return [
        ReadingSessionSchema.model_validate(session) for session in reading_sessions
    ]


async def get_user_reading_session(
    username: str, session: AsyncSession, limit: int = None
) -> list[ReadingSessionSchema]:
    statement = (
        select(ReadingSession)
        .join(ReadingSession.user)
        .where(User.username == username)
        .options(joinedload(ReadingSession.book), joinedload(ReadingSession.user))
        .order_by(ReadingSession.started_at.desc())
    )

    if limit is not None:
        statement = statement.limit(limit)

    result = await session.execute(statement)
    reading_sessions = result.scalars().all()

    return [
        ReadingSessionSchema.model_validate(session) for session in reading_sessions
    ]


async def get_user_book_reading_session(
    username: str, book_id: int, session: AsyncSession
) -> list[ReadingSessionSchema]:

    statement = (
        select(ReadingSession)
        .join(ReadingSession.user)
        .where(
            User.username == username,
            ReadingSession.book_id == book_id,
        )
        .options(joinedload(ReadingSession.book), joinedload(ReadingSession.user))
        .order_by(ReadingSession.started_at.desc())
    )

    result = await session.execute(statement)
    reading_sessions = result.scalars().all()

    return [
        ReadingSessionSchema.model_validate(session) for session in reading_sessions
    ]


async def get_reading_session_by_id(
    session: AsyncSession, session_id: int
) -> ReadingSession | None:
    statement = (
        select(ReadingSession)
        .where(ReadingSession.id == session_id)
        .options(joinedload(ReadingSession.book), joinedload(ReadingSession.user))
    )

    result = await session.execute(statement)
    return result.scalar_one_or_none()


async def create_reading_session(
    session: AsyncSession, data: ReadingSessionCreate
) -> ReadingSession:

    user = select(User).where(User.username == data.username)
    result = await session.execute(user)
    user_db = result.scalar_one_or_none()

    if not user_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"user with username {data.username} was not found",
        )

    association_statement = select(UserBookAssociation).where(
        UserBookAssociation.user_id == user_db.id,
        UserBookAssociation.book_id == data.book_id,
    )
    association_result = await session.execute(association_statement)
    association = association_result.scalar_one_or_none()

    if association:
        if association.status != BookReadStatus.READING:
            association.status = BookReadStatus.READING

    else:
        new_association = UserBookAssociation(
            user_id=user_db.id, book_id=data.book_id, status=BookReadStatus.READING
        )
        session.add(new_association)

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
    update_data = reading_session_update.model_dump(exclude_unset=partial)

    for key, value in update_data.items():
        setattr(reading_session, key, value)

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

    await session.delete(reading_session)
    await session.commit()
    return True
