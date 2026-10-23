from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from loguru import logger
from fastapi import HTTPException, status

from core.models import BookCollection, Book, User
from entities.book_collections.schema import (
    BookCollectionCreate,
    BookCollectionUpdate,
    BookCollectionUpdatePartial,
)


async def get_user_collections(
    session: AsyncSession, username: str
) -> list[BookCollection]:
    logger.info(f"Try to get all collections for user { username }")

    statement = (
        select(BookCollection)
        .join(User, BookCollection.user_id == User.id)
        .where(User.username == username)
        .options(
            selectinload(BookCollection.books).selectinload(Book.authors),
            selectinload(BookCollection.books).selectinload(Book.genres),
        )
        .order_by(desc(BookCollection.created_at))
    )

    result = await session.execute(statement)
    return list(result.scalars().unique().all())


async def get_collection_by_id(
    session: AsyncSession, collection_id: int, username: str
) -> BookCollection | None:
    logger.info(f"Try to get collection with id {collection_id} for user {username}")

    statement = (
        select(BookCollection)
        .join(User, BookCollection.user_id == User.id)
        .where(BookCollection.id == collection_id, User.username == username)
        .options(
            selectinload(BookCollection.books).selectinload(Book.authors),
            selectinload(BookCollection.books).selectinload(Book.genres),
        )
    )

    result = await session.execute(statement)
    collection = result.scalar_one_or_none()

    if not collection:
        logger.error(
            f"Failed to get collection with id {collection_id} for user {username}: not found"
        )
        return None
    return collection


async def create_collection(
    session: AsyncSession, username: str, data: BookCollectionCreate
) -> BookCollection:
    logger.info(f"Try to create collection '{data.title}' for user username")

    user_statement = select(User.id).where(User.username == username)
    user_result = await session.execute(user_statement)
    user_id = user_result.scalar_one_or_none()

    if not user_id:
        logger.error(f"Failed to create collection: user {username} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Користувача '{username} не знайдено'",
        )

    collection_data = data.model_dump(exclude={"book_ids"})
    collection = BookCollection(**collection_data, user_id=user_id)

    if data.book_ids:
        book_statement = select(Book).where(Book.id.in_(data.book_ids))
        book_result = await session.execute(book_statement)
        books = list(book_result.scalars().all())
        collection.books = books

    session.add(collection)
    await session.commit()
    await session.refresh(collection)

    return await get_collection_by_id(session, collection.id, username)


async def update_collection(
    session: AsyncSession,
    collection: BookCollection,
    collection_update: BookCollectionUpdate | BookCollectionUpdatePartial,
    partial: bool = False,
) -> BookCollection:
    logger.info(f"Try to update collection id {collection.id}")

    update_data = collection_update.model_dump(
        exclude_unset=partial, exclude={"book_ids"}
    )
    for key, value in update_data.items():
        setattr(collection, key, value)

    if (
        hasattr(collection_update, "book_ids")
        and collection_update.book_ids is not None
    ):
        books_statement = select(Book).where(Book.id.in_(collection_update.book_ids))
        books_result = await session.execute(books_statement)
        collection.books = list(books_result.scalars().all())

    await session.commit()
    await session.refresh(collection)
    return collection


async def delete_collection(
    session: AsyncSession, collection_id: int, username: str
) -> bool:
    logger.info(f"Try to delete collection with id {collection_id} for user {username}")

    collection = await get_collection_by_id(session, collection_id, username)

    if not collection:
        return False

    await session.delete(collection)
    await session.commit()
    return True


async def add_book_to_collection(
    session: AsyncSession, collection_id: int, book_id: int, username: str
) -> BookCollection:
    logger.info(f"Try to add book id {book_id} to collection id {collection_id}")

    collection = await get_collection_by_id(session, collection_id, username)

    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Колекцію не знайдено"
        )

    book_statement = select(Book).where(Book.id == book_id)
    book_result = await session.execute(book_statement)
    book = book_result.scalar_one_or_none()

    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Книгу не знайдено"
        )

    if book not in collection.books:
        collection.books.append(book)
        await session.commit()
        await session.refresh(collection)

    return collection


async def remove_book_from_collection(
    session: AsyncSession, collection_id: int, book_id: int, username: str
) -> BookCollection:
    logger.info(f"Try to remove book id {book_id} from collection id {collection_id}")

    collection = await get_collection_by_id(session, collection_id, username)
    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Колекцію не знайдено"
        )

    collection.books = [b for b in collection.books if b.id != book_id]
    await session.commit()
    await session.refresh(collection)

    return collection
