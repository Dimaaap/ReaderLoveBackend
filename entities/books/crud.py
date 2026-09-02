import asyncio
from fastapi import status, HTTPException
from datetime import datetime, timezone, timedelta

from loguru import logger
from sqlalchemy import select, func, case, desc, cast, Date, or_
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
    BookReview,
    BookPublisher,
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
    UserBookStatusUpdate,
)


async def search_crud(statement, search):
    search = search.strip()

    author_full_name = func.concat(BookAuthors.first_name, " ", BookAuthors.last_name)
    statement = statement.where(
        or_(
            Book.title.ilike(f"%{search}%"),
            Book.isbn.ilike(f"%{search}%"),
            Book.authors.any(
                or_(
                    BookAuthors.first_name.ilike(f"%{search}%"),
                    BookAuthors.last_name.ilike(f"%{search}%"),
                    author_full_name.ilike(f"%{search}%"),
                )
            ),
        )
    )

    return statement


async def get_all_books(
    session: AsyncSession, limit: int | None = None, search: str | None = None
) -> list[BookSchema]:

    logger.info(f"Try to get all books with params: search={search}, limit={limit}")
    statement = (
        select(Book)
        .options(selectinload(Book.authors), selectinload(Book.genres))
        .order_by(Book.id)
    )

    if search:
        statement = await search_crud(statement, search)

    if limit is not None:
        statement = statement.limit(limit)

    result = await session.execute(statement)

    books = result.scalars().unique().all()
    return [BookSchema.model_validate(book) for book in books]


async def get_book_by_id_without_username(
    session: AsyncSession, book_id: int
) -> BookSchema | None:
    logger.info(f"Try to get book with id {book_id}")
    statement = (
        select(Book)
        .where(Book.id == book_id)
        .options(
            selectinload(Book.authors),
            selectinload(Book.genres),
            selectinload(Book.publisher),
        )
    )

    result = await session.execute(statement)
    book = result.scalar_one_or_none()

    if not book:
        logger.error(f"Failed to get book with id {book_id} - book was not found in db")
        return None

    return BookSchema.model_validate(book)


async def get_book_by_id(
    session: AsyncSession, book_id: int, username: str
) -> BookSchemaWithSessions | None:
    logger.info(f"Try to get book with id {book_id}")
    statement = (
        select(Book)
        .where(Book.id == book_id)
        .options(
            selectinload(Book.authors),
            selectinload(Book.genres),
            selectinload(Book.publisher),
        )
    )

    result = await session.execute(statement)
    book = result.scalar_one_or_none()

    if not book:
        logger.error(f"Failed to get book with id {book_id} - book was not found in db")
        return None

    book_detail = BookDetailSchema.model_validate(book)

    if username:
        user_stmt = (
            select(
                User.id, UserBookAssociation.last_read_page, UserBookAssociation.status
            )
            .outerjoin(
                UserBookAssociation,
                (UserBookAssociation.user_id == User.id)
                & (UserBookAssociation.book_id == book.id),
            )
            .where(User.username == username)
        )
        user_result = await session.execute(user_stmt)
        user_row = user_result.first()

        if user_row:
            user_id, last_read_page, status_val = user_row
            logger.info(
                f"Get user data for book - {user_id}, {last_read_page}, {status_val}"
            )

            book_detail.read_pages = last_read_page or 0
            book_detail.status = (
                status_val.value if hasattr(status_val, "value") else status_val
            )

            if user_id:
                stats_statement = select(
                    func.count(ReadingSession.id).label("sessions_count"),
                    func.max(
                        case(
                            (ReadingSession.ended_at.is_(None), ReadingSession.id),
                            else_=None,
                        )
                    ).label("active_session_id"),
                ).where(
                    ReadingSession.book_id == book.id, ReadingSession.user_id == user_id
                )

                stats_result = await session.execute(stats_statement)
                stats = stats_result.one()

                book_detail.reading_sessions_count = stats.sessions_count
                book_detail.active_session_id = stats.active_session_id
                logger.info(
                    f"Calculated reading sessions count and active session_id for book: {stats.sessions_count}"
                    f"{status.active_session_id}"
                )

    return BookSchemaWithSessions.model_validate(book)


async def get_book_by_slug(session: AsyncSession, book_slug: str) -> Book | None:
    logger.info(f"Try to get book with slug {book_slug}")

    statement = (
        select(Book)
        .where(Book.slug == book_slug)
        .options(selectinload(Book.authors), selectinload(Book.genres))
    )

    result = await session.execute(statement)
    return result.scalar_one_or_none()


async def get_book_by_slug_for_user_with_status(
    session: AsyncSession, book_slug: str, username: str
) -> Book | None:
    logger.info(f"Try to get book {book_slug} for user {username}")
    statement = (
        select(
            Book,
            UserBookAssociation.status,
            UserBookAssociation.last_read_page,
            User.id.label("user_id"),
        )
        .outerjoin(UserBookAssociation, (UserBookAssociation.book_id == Book.id))
        .outerjoin(
            User, (UserBookAssociation.user_id == User.id) & (User.username == username)
        )
        .where(Book.slug == book_slug)
        .options(
            selectinload(Book.authors),
            selectinload(Book.genres),
            selectinload(Book.reviews).selectinload(BookReview.user),
        )
    )

    result = await session.execute(statement)
    row = result.first()

    if not row:
        logger.error(f"Failed to get book {book_slug} for user {username}")
        return None

    book, status, last_read_page, user_id = row
    book_detail = BookDetailSchema.model_validate(book)

    if user_id:
        stats_statement = select(
            func.count(ReadingSession.id).label("sessions_count"),
            func.max(
                case((ReadingSession.ended_at.is_(None), ReadingSession.id), else_=None)
            ).label("active_session_id"),
        ).where(ReadingSession.book_id == book.id, ReadingSession.user_id == user_id)

        stats_result = await session.execute(stats_statement)
        stats = stats_result.one()

        book_detail.reading_sessions_count = stats.sessions_count
        book_detail.active_session_id = stats.active_session_id
        logger.info(
            f"Uploaded sessions cound and active session id for book {book_slug} for user {username}: "
            f"{stats.sessions_count}, {stats.active_session_id}"
        )

    book_detail.read_pages = last_read_page or 0
    book_detail.status = status

    return book_detail.model_dump(by_alias=False)


async def delete_user_book_status(
    session: AsyncSession, username: str, book_slug: str
) -> bool:
    logger.info(
        f"Try to delete reading book status in book {book_slug} for user {username}"
    )
    statement = (
        select(UserBookAssociation)
        .join(User, UserBookAssociation.user_id == User.id)
        .join(Book, UserBookAssociation.book_id == Book.id)
        .where(User.username == username, Book.slug == book_slug)
    )

    result = await session.execute(statement)
    assoc = result.scalar_one_or_none()
    logger.info(assoc)

    if assoc:
        await session.delete(assoc)
        await session.commit()
        return True

    return False


async def get_book_by_slug_for_user_with_sessions_stats(
    session: AsyncSession, book_slug: str, username: str, limit: int = 5
) -> BookSchemaWithSessions | None:
    logger.info(
        f"Try to get book {book_slug} with reading sessions for user {username} with limit={limit}"
    )
    book_statement = (
        select(Book)
        .where(Book.slug == book_slug)
        .options(selectinload(Book.authors), selectinload(Book.genres))
    )
    book_result = await session.execute(book_statement)
    book = book_result.scalar_one_or_none()

    if not book:
        logger.error(
            f"Failed to get book {book_slug} with reading sessions for user {username} with limit={limit}"
        )
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

    latest_session_stmt = (
        select(ReadingSession.end_page)
        .where(ReadingSession.book_id == book.id, ReadingSession.user_id == user_id)
        .order_by(desc(ReadingSession.started_at))
        .limit(1)
    )
    latest_session_result = await session.execute(latest_session_stmt)
    latest_end_page = latest_session_result.scalar_one_or_none()

    if latest_end_page is not None:
        read_pages = latest_end_page
    else:
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


async def set_user_book_status(
    session: AsyncSession, username: str, book_slug: str, data: UserBookStatusUpdate
) -> UserBookAssociation:
    logger.info(
        f"Try to set book status in book {book_slug} for user {username} with data {data}"
    )
    user_statement = select(User.id).where(User.username == username)
    user_res = await session.execute(user_statement)
    user_id = user_res.scalar_one_or_none()

    if not user_id:
        logger.error(
            f"Failed to set book status in book {book_slug} for user {username} - user was not found"
        )
        raise ValueError("User not found")

    book_statement = select(Book.id).where(Book.slug == book_slug)
    book_res = await session.execute(book_statement)
    book_id = book_res.scalar_one_or_none()

    if not book_id:
        logger.error(
            f"Failed to set book status in book {book_slug} for user {username} - book was not found"
        )
        raise ValueError("Book not found")

    assoc_statement = select(UserBookAssociation).where(
        UserBookAssociation.user_id == user_id, UserBookAssociation.book_id == book_id
    )

    assoc_res = await session.execute(assoc_statement)
    assoc = assoc_res.scalar_one_or_none()

    if assoc:
        assoc.status = data.status
        if data.last_read_page is not None:
            assoc.last_read_page = data.last_read_page
    else:
        assoc = UserBookAssociation(
            user_id=user_id,
            book_id=book_id,
            status=data.status,
            last_read_page=data.last_read_page or 0,
        )
        session.add(assoc)

    latest_session_statement = (
        select(ReadingSession.end_page)
        .where(ReadingSession.book_id == book_id, ReadingSession.user_id == user_id)
        .order_by(desc(ReadingSession.started_at))
        .limit(1)
    )
    latest_session_res = await session.execute(latest_session_statement)
    latest_end_page = latest_session_res.scalar_one_or_none()

    if data.last_read_page is not None:
        logger.info(
            f"Added last_read_page for book {book_slug}: last read page is {data.last_read_page}"
        )
        assoc.last_read_page = data.last_read_page

    elif latest_end_page is not None:
        logger.info(
            f"Added last_read_page for book {book_slug}: last read page is {latest_end_page}"
        )
        assoc.last_read_page = latest_end_page

    await session.commit()
    await session.refresh(assoc)
    return assoc


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
    logger.info(f"Try to get book {book_slug} for user {username}")
    book_statement = (
        select(Book)
        .where(Book.slug == book_slug)
        .options(
            selectinload(Book.authors),
            selectinload(Book.genres),
            selectinload(Book.publisher),
            selectinload(Book.reviews).options(selectinload(BookReview.user)),
        )
    )
    book_result = await session.execute(book_statement)
    book = book_result.scalar_one_or_none()

    if not book:
        logger.error(
            f"Failed to get book {book_slug} for user {username} - book was not found"
        )
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

    sessions_count = 0
    active_session_id = None
    last_read_page = 0

    if not user_row:
        user_id, last_read_page = user_row

        stats_statement = select(
            func.count(ReadingSession.id).label("sessions_count"),
            func.max(
                case((ReadingSession.ended_at.is_(None), ReadingSession.id), else_=None)
            ).label("active_session_id"),
        ).where(ReadingSession.book_id == book.id, ReadingSession.user_id == user_id)

        stats_result = await session.execute(stats_statement)
        stats = stats_result.one()

        sessions_count = stats.sessions_count
        active_session_id = stats.active_session_id
        logger.info(
            f"sessions count {stats.sessions_count} active session id {stats.active_session_id}"
        )

    book.reading_sessions_count = sessions_count
    book.read_pages = last_read_page or 0
    book.active_session_id = active_session_id

    return BookDetailSchema.model_validate(book)


async def get_current_main_reading_book(
    session: AsyncSession, username: str, limit: int = 5
) -> BookSchemaWithSessions | None:
    logger.info(f"Try to get current book for user {username}")
    user_statement = select(User.id).where(User.username == username)
    user_result = await session.execute(user_statement)
    user_id = user_result.scalar_one_or_none()

    if not user_id:
        logger.error(
            f"Failed to get current book for user {username} - user was not found"
        )
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
        logger.info(f"Not found book with reading sessions")
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
    book_data = data.model_dump(exclude={"authors", "genres", "publisher"})
    logger.info(f"Try to create book with data {book_data}")
    book = Book(**book_data)

    if data.authors:
        authors = []

        for author_data in data.authors:
            author_statement = select(BookAuthors).where(
                BookAuthors.first_name == author_data.first_name,
                BookAuthors.last_name == author_data.last_name,
            )
            author_result = await session.execute(author_statement)
            author = author_result.scalar_one_or_none()

            if author is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=(
                        f"Автор "
                        f"{author_data.first_name} "
                        f"{author_data.last_name} "
                        f"не знайдений"
                    ),
                )
            authors.append(author)

        book.authors = authors

    if data.genres:
        genres_statement = select(BookGenres).where(BookGenres.title.in_(data.genres))
        genres_result = await session.execute(genres_statement)
        fetched_genres = list(genres_result.scalars().all())

        book.genres = fetched_genres

    if data.publisher:
        publisher_statement = select(BookPublisher).where(
            BookPublisher.slug == data.publisher
        )

        publisher_result = await session.execute(publisher_statement)
        publisher = publisher_result.scalar_one_or_none()

        if publisher is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Видавництво '{data.publisher}' не знайдене",
            )

        book.publisher = publisher

    session.add(book)
    await session.flush()

    book_id = book.id

    await session.commit()

    statement = (
        select(Book)
        .options(
            selectinload(Book.authors),
            selectinload(Book.genres),
            selectinload(Book.publisher),
        )
        .where(Book.id == book_id)
    )

    result = await session.execute(statement)

    book = result.scalar_one()

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
    for book, status_val, last_read_page in result.all():
        base_book_schema = BookSchema.model_validate(book)

        book_dict = base_book_schema.model_dump()

        book_dict["status"] = (
            status_val.value if hasattr(status_val, "value") else str(status_val)
        )
        book_dict["last_read_page"] = last_read_page or 0

        user_books.append(UserBookSchema(**book_dict))

    return user_books


async def delete_book(session: AsyncSession, book_id: int) -> bool:
    statement = select(Book).where(Book.id == book_id)

    book_res = await session.execute(statement)
    book = book_res.scalar_one_or_none()

    if not book:
        return False

    await session.delete(book)
    await session.commit()
    return True


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
