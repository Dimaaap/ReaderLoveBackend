import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.models import (
    Book,
    BookGenres,
    BookAuthors,
    db_helper,
    UserBookAssociation,
    User,
)
from core.models.user_book_association import BookReadStatus
from .data import books
from entities.books.schema import BookSchema, BookCreate, BookUpdate, BookUpdatePartial


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
) -> list[BookSchema]:
    statement = (
        select(Book)
        .join(UserBookAssociation, Book.id == UserBookAssociation.book_id)
        .join(User, UserBookAssociation.user_id == User.id)
        .where(
            User.username == username,
            UserBookAssociation.status.in_(
                [BookReadStatus.READING, BookReadStatus.FINISHED]
            ),
        )
        .options(selectinload(Book.authors), selectinload(Book.genres))
        .order_by(Book.title)
    )

    result = await session.execute(statement)
    books = result.scalars().all()

    return [BookSchema.model_validate(book) for book in books]


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
