import asyncio
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.models import (
    Book,
    BookGenres,
    BookAuthors,
    db_helper,
    UserBookAssociation,
    User,
    ReadingSession,
)
from core.models.user_book_association import BookReadStatus
from .data import books
from entities.books.schema import (
    BookSchema,
    BookCreate,
    BookUpdate,
    BookUpdatePartial,
    UserBookSchema,
    BookDetailSchema,
    BookSchemaWithSessions,
    MiniReadingSessionSchema,
)


async def get_all_books(session: AsyncSession) -> list[BookSchema]:
    statement = (
        select(Book)
        .options(selectinload(Book.authors), selectinload(Book.genres))
        .order_by(Book.id)
    )

    result = await session.execute(statement)

    books = result.scalars().all()
    return [BookSchema.model_validate(book) for book in books]


async def get_book_by_id(session: AsyncSession, book_id: int) -> Book | None:
    statement = (
        select(Book)
        .where(Book.id == book_id)
        .options(selectinload(Book.authors), selectinload(Book.genres))
    )

    result = await session.execute(statement)
    return result.scalar_one_or_none()


async def get_book_by_slug(session: AsyncSession, book_slug: str) -> Book | None:
    statement = (
        select(Book)
        .where(Book.slug == book_slug)
        .options(selectinload(Book.authors), selectinload(Book.genres))
    )

    result = await session.execute(statement)
    return result.scalar_one_or_none()


async def get_book_by_slug_for_user_with_sessions_stats(
    session: AsyncSession, book_slug: str, username: str
) -> BookSchemaWithSessions | None:
    book_statement = (
        select(Book)
        .where(Book.slug == book_slug)
        .options(selectinload(Book.authors), selectinload(Book.genres))
    )
    book_result = await session.execute(book_statement)
    book = book_result.scalar_one_or_none()

    if not book:
        return None

    user_statement = select(User.id).where(User.username == username)
    user_result = await session.execute(user_statement)
    user_id = user_result.scalar_one_or_none()

    if not user_id:
        book_data = BookSchema.model_validate(book).model_dump()
        return BookSchemaWithSessions(**book_data)

    stats_statement = select(
        func.count(ReadingSession.id).label("sessions_count"),
        func.coalesce(func.max(ReadingSession.end_page), 0).label("max_end_page"),
    ).where(ReadingSession.book_id == book.id, ReadingSession.user_id == user_id)

    stats_result = await session.execute(stats_statement)
    stats = stats_result.one()

    active_session_statement = (
        select(ReadingSession.id)
        .where(
            ReadingSession.book_id == book.id,
            ReadingSession.user_id == user_id,
            ReadingSession.ended_at.is_(None),
        )
        .limit(1)
    )

    active_session_result = await session.execute(active_session_statement)
    active_session_id = active_session_result.scalar_one_or_none()

    recent_session_statement = (
        select(ReadingSession)
        .where(ReadingSession.book_id == book.id, ReadingSession.user_id == user_id)
        .order_by(desc(ReadingSession.started_at))
        .limit(5)
    )

    recent_sessions_result = await session.execute(recent_session_statement)
    db_recent_sessions = recent_sessions_result.scalars().all()

    recent_sessions = [
        MiniReadingSessionSchema.model_validate(session)
        for session in db_recent_sessions
    ]

    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    weekly_sessions_statement = select(ReadingSession).where(
        ReadingSession.book_id == book.id,
        ReadingSession.user_id == user_id,
        ReadingSession.started_at >= seven_days_ago,
        ReadingSession.end_page.isnot(None),
    )
    weekly_result = await session.execute(weekly_sessions_statement)
    weekly_sessions = weekly_result.scalars().all()

    weekly_pages = sum(
        (s.end_page - s.start_page)
        for s in weekly_sessions
        if s.end_page >= s.start_page
    )

    book_base_data = BookSchema.model_validate(book).model_dump()
    book_base_data["reading_sessions_count"] = stats.sessions_count
    book_base_data["read_pages"] = stats.max_end_page
    book_base_data["weekly_read_pages"] = weekly_pages
    book_base_data["active_session_id"] = active_session_id
    book_base_data["recent_sessions"] = recent_sessions

    return BookSchemaWithSessions.model_validate(book_base_data)


async def get_book_by_slug_for_user(
    session: AsyncSession, book_slug: str, username: str
) -> BookDetailSchema | None:
    book_statement = (
        select(Book)
        .where(Book.slug == book_slug)
        .options(selectinload(Book.authors), selectinload(Book.genres))
    )
    book_result = await session.execute(book_statement)
    book = book_result.scalar_one_or_none()

    if not book:
        return None

    user_statement = select(User.id).where(User.username == username)
    user_result = await session.execute(user_statement)
    user_id = user_result.scalar_one_or_none()

    if not user_id:
        book_data = BookSchema.model_validate(book).model_dump()
        return BookDetailSchema(**book_data)

    stats_statement = select(
        func.count(ReadingSession.id).label("sessions_count"),
        func.coalesce(func.max(ReadingSession.end_page), 0).label("max_end_page"),
    ).where(ReadingSession.book_id == book.id, ReadingSession.user_id == user_id)

    stats_result = await session.execute(stats_statement)
    stats = stats_result.one()

    active_session_statement = (
        select(ReadingSession.id)
        .where(
            ReadingSession.book_id == book.id,
            ReadingSession.user_id == user_id,
            ReadingSession.ended_at.is_(None),
        )
        .limit(1)
    )

    active_session_result = await session.execute(active_session_statement)
    active_session_id = active_session_result.scalar_one_or_none()

    book_base_data = BookSchema.model_validate(book).model_dump()
    book_base_data["reading_sessions_count"] = stats.sessions_count
    book_base_data["read_pages"] = stats.max_end_page
    book_base_data["active_session_id"] = active_session_id

    return BookDetailSchema.model_validate(book_base_data)


async def get_current_main_reading_book(
    session: AsyncSession, username: str
) -> BookSchemaWithSessions | None:
    user_statement = select(User.id).where(User.username == username)
    user_result = await session.execute(user_statement)
    user_id = user_result.scalar_one_or_none()

    if not user_id:
        return None

    active_session_statement = (
        select(Book.slug)
        .join(ReadingSession, Book.id == ReadingSession.book_id)
        .where(ReadingSession.user_id == user_id, ReadingSession.ended_at.is_(None))
        .limit(1)
    )
    result = await session.execute(active_session_statement)
    book_slug = result.scalar_one_or_none()

    if not book_slug:
        last_read_statement = (
            select(Book.slug)
            .join(ReadingSession, Book.id == ReadingSession.book_id)
            .join(UserBookAssociation, Book.id == UserBookAssociation.book_id)
            .where(
                ReadingSession.user_id == user_id,
                UserBookAssociation.user_id == user_id,
                UserBookAssociation.status == BookReadStatus.READING,
            )
            .order_by(desc(ReadingSession.started_at))
            .limit(1)
        )
        result = await session.execute(last_read_statement)
        book_slug = result.scalar_one_or_none()
        print(book_slug)

    if not book_slug:
        fallback_statement = (
            select(Book.slug)
            .join(UserBookAssociation, Book.id == UserBookAssociation.book_id)
            .where(
                UserBookAssociation.user_id == user_id,
                UserBookAssociation.status == BookReadStatus.READING,
            )
            .order_by(desc(UserBookAssociation.updated_at))
            .limit(1)
        )
        result = await session.execute(fallback_statement)
        book_slug = result.scalar_one_or_none()

    if book_slug:
        return await get_book_by_slug_for_user_with_sessions_stats(
            session, book_slug, username
        )

    return None


async def create_book(session: AsyncSession, data: BookCreate) -> Book:
    book_data = data.model_dump(exclude={"authors", "genres"})
    book = Book(**book_data)

    if data.authors:
        author_last_names = [author.last_name for author in data.authors]
        author_statement = select(BookAuthors).where(
            BookAuthors.last_name.in_(author_last_names)
        )
        author_result = await session.execute(author_statement)
        fetched_authors = list(author_result.scalars().all())
        print(f"Знайдені автори: {fetched_authors}")
        book.authors = fetched_authors

    if data.genres:
        genres_statement = select(BookGenres).where(BookGenres.title.in_(data.genres))
        genres_result = await session.execute(genres_statement)
        fetched_genres = list(genres_result.scalars().all())

        print(f"Знайдені жанри: {fetched_genres}")
        book.genres = fetched_genres

    session.add(book)
    await session.commit()
    await session.refresh(book)
    return book


async def update_book(
    session: AsyncSession,
    book: Book,
    book_update: BookUpdate | BookUpdatePartial,
    partial: bool = False,
) -> Book:
    update_data = book_update.model_dump(
        exclude_unset=partial, exclude={"authors", "genres"}
    )

    for key, value in update_data.items():
        setattr(book, key, value)

    if book_update.authors is not None:
        author_last_names = [author.last_name for author in book_update.authors]
        authors_stmt = select(BookAuthors).where(
            BookAuthors.last_name.in_(author_last_names)
        )
        authors_result = await session.execute(authors_stmt)
        book.authors = list(authors_result.scalars().all())

    if book_update.genres is not None:
        genres_stmt = select(BookGenres).where(BookGenres.title.in_(book_update.genres))
        genres_result = await session.execute(genres_stmt)
        book.genres = list(genres_result.scalars().all())

    await session.commit()
    await session.refresh(book)
    return book


async def get_user_active_books_for_notes(
    username: str, session: AsyncSession
) -> list[UserBookSchema]:
    statement = (
        select(Book, UserBookAssociation.status)
        .join(UserBookAssociation, Book.id == UserBookAssociation.book_id)
        .join(User, UserBookAssociation.user_id == User.id)
        .where(User.username == username)
        .options(selectinload(Book.authors), selectinload(Book.genres))
        .order_by(Book.title)
    )

    result = await session.execute(statement)

    user_books = []
    for book, status in result.all():
        book_data = BookSchema.model_validate(book).model_dump()
        book_data["status"] = status
        user_books.append(UserBookSchema.model_validate(book_data))

    return user_books


async def delete_book(session: AsyncSession, book: Book) -> None:
    await session.delete(book)
    await session.commit()


async def seed_books(session: AsyncSession):
    for book in books:
        book["publish_date"] = str(book["publish_date"])
        book_create = BookCreate(**book)
        await create_book(session, book_create)
    print("Successfully")


async def main():
    async with db_helper.session_factory() as session:
        await seed_books(session)
    pass


if __name__ == "__main__":
    asyncio.run(main())
