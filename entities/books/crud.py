import asyncio
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, func, case, desc, cast, Date
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
from entities.books.utils import calculate_streak
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
    session: AsyncSession, book_slug: str, username: str, limit: int = 5
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

    user_stmt = (
        select(User.id, UserBookAssociation.last_read_page)
        .outerjoin(
            UserBookAssociation,
            (UserBookAssociation.user_id == User.id)
            & (UserBookAssociation.book_id == book.id),
        )
        .where(User.username == username)
    )
    user_result = await session.execute(user_stmt)
    user_row = user_result.first()

    if not user_row:
        book_data = BookSchema.model_validate(book).model_dump()
        return BookSchemaWithSessions(**book_data)

    user_id, assoc_last_read_page = user_row
    read_pages = assoc_last_read_page if assoc_last_read_page is not None else 0

    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)

    stats_statement = select(
        func.count(ReadingSession.id).label("sessions_count"),
        func.max(
            case((ReadingSession.ended_at.is_(None), ReadingSession.id), else_=None)
        ).label("active_session_id"),
        func.coalesce(
            func.sum(
                case(
                    (
                        (ReadingSession.started_at >= seven_days_ago)
                        & (ReadingSession.end_page >= ReadingSession.start_page),
                        ReadingSession.end_page - ReadingSession.start_page,
                    ),
                    else_=0,
                )
            ),
            0,
        ).label("weekly_pages"),
    ).where(ReadingSession.book_id == book.id, ReadingSession.user_id == user_id)

    stats_result = await session.execute(stats_statement)
    stats = stats_result.one()

    recent_session_statement = (
        select(ReadingSession)
        .where(ReadingSession.book_id == book.id, ReadingSession.user_id == user_id)
        .order_by(desc(ReadingSession.started_at))
        .limit(limit)
    )
    recent_sessions_result = await session.execute(recent_session_statement)
    db_recent_sessions = recent_sessions_result.scalars().all()

    recent_sessions = [
        MiniReadingSessionSchema.model_validate(s) for s in db_recent_sessions
    ]

    dates_statement = (
        select(cast(ReadingSession.started_at, Date))
        .where(ReadingSession.book_id == book.id, ReadingSession.user_id == user_id)
        .distinct()
        .order_by(desc(cast(ReadingSession.started_at, Date)))
    )
    dates_result = await session.execute(dates_statement)
    reading_dates = dates_result.scalars().all()
    current_streak = calculate_streak(reading_dates)

    book_base_data = BookSchema.model_validate(book).model_dump()
    book_base_data.update(
        {
            "reading_sessions_count": stats.sessions_count,
            "read_pages": read_pages,
            "weekly_read_pages": stats.weekly_pages,
            "active_session_id": stats.active_session_id,
            "recent_sessions": recent_sessions,
            "current_streak": current_streak,
        }
    )

    return BookSchemaWithSessions.model_validate(book_base_data)


async def get_user_library_for_export(
    session: AsyncSession,
    username: str,
    status_filter: str = "all",
    include_notes: bool = True,
) -> list[dict]:
    statement = (
        select(Book, UserBookAssociation.status, UserBookAssociation.last_read_page)
        .join(UserBookAssociation, Book.id == UserBookAssociation.book_id)
        .join(User, UserBookAssociation.user_id == User.id)
        .where(User.username == username)
        .options(selectinload(Book.authors), selectinload(Book.genres))
    )

    status_map = {
        "want_to_read": BookReadStatus.WANT_TO_READ,
        "reading": BookReadStatus.READING,
        "finished": BookReadStatus.FINISHED,
        "paused": BookReadStatus.PAUSED,
        "abandoned": BookReadStatus.ABANDONED,
    }

    if status_filter in status_map:
        statement = statement.where(
            UserBookAssociation.status == status_map[status_filter]
        )

    if include_notes:
        statement = statement.options(selectinload(Book.notes))

    result = await session.execute(statement)
    rows = result.all()

    export_data = []

    for book, status_val, last_read_page in rows:
        item = {
            "title": book.title,
            "authors": ", ".join(
                [
                    (
                        f"{a.first_name} {a.last_name}"
                        if hasattr(a, "first_name") and a.first_name
                        else a.last_name
                    )
                    for a in book.authors
                ]
            ),
            "genres": ", ".join([g.title for g in book.genres]),
            "pages": getattr(book, "pages_count", getattr(book, "pages", None)),
            "last_read_page": last_read_page or 0,
            "status": (
                status_val.value if hasattr(status_val, "value") else str(status_val)
            ),
        }

        if include_notes:
            notes_list = getattr(book, "notes", [])
            item["notes"] = [n.note_text for n in notes_list] if notes_list else []

        export_data.append(item)

    return export_data


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

    user_assoc_stmt = (
        select(User.id, UserBookAssociation.last_read_page)
        .outerjoin(
            UserBookAssociation,
            (UserBookAssociation.user_id == User.id)
            & (UserBookAssociation.book_id == book.id),
        )
        .where(User.username == username)
    )
    result = await session.execute(user_assoc_stmt)
    user_row = result.first()

    if not user_row:
        book_data = BookSchema.model_validate(book).model_dump()
        return BookDetailSchema(**book_data)

    user_id, last_read_page = user_row

    stats_statement = select(
        func.count(ReadingSession.id).label("sessions_count"),
        func.max(
            case((ReadingSession.ended_at.is_(None), ReadingSession.id), else_=None)
        ).label("active_session_id"),
    ).where(ReadingSession.book_id == book.id, ReadingSession.user_id == user_id)

    stats_result = await session.execute(stats_statement)
    stats = stats_result.one()

    book_base_data = BookSchema.model_validate(book).model_dump()
    book_base_data.update(
        {
            "reading_sessions_count": stats.sessions_count,
            "read_pages": last_read_page or 0,
            "active_session_id": stats.active_session_id,
        }
    )

    return BookDetailSchema.model_validate(book_base_data)


async def get_current_main_reading_book(
    session: AsyncSession, username: str, limit: int = 5
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
            session, book_slug, username, limit
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
        select(Book, UserBookAssociation.status, UserBookAssociation.last_read_page)
        .join(UserBookAssociation, Book.id == UserBookAssociation.book_id)
        .join(User, UserBookAssociation.user_id == User.id)
        .where(User.username == username)
        .options(selectinload(Book.authors), selectinload(Book.genres))
        .order_by(Book.title)
    )

    result = await session.execute(statement)

    user_books = []
    for book, status, last_read_page in result.all():
        book_data = BookSchema.model_validate(book).model_dump()
        book_data["status"] = status
        book_data["last_read_page"] = last_read_page or 0
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
