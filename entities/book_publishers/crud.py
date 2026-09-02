from fastapi import HTTPException, status

from loguru import logger
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import BookPublisher
from entities.book_publishers.schema import (
    BookPublisherCreate,
    BookPublisherSchema,
    BookPublisherUpdate,
    BookPublisherUpdatePublisher,
)


async def get_all_book_publishers(
    session: AsyncSession, limit: int = 10, offset: int = 0
) -> list[BookPublisherSchema]:
    logger.info(
        f"Try to get all book publishers with queries: limit={limit}, offset={offset}"
    )
    statement = (
        select(BookPublisher)
        .options(joinedload(BookPublisher.books))
        .order_by(BookPublisher.id)
        .offset(offset)
        .limit(limit)
    )
    result = await session.execute(statement)
    book_publishers = result.unique().scalars().all()

    return [
        BookPublisherSchema.model_validate(publisher) for publisher in book_publishers
    ]


async def get_book_publisher_by_id(
    session: AsyncSession, publisher_id: int
) -> BookPublisherSchema | None:
    logger.info(f"Try to get book publisher {publisher_id}")
    statement = (
        select(BookPublisher)
        .where(BookPublisher.id == publisher_id)
        .options(joinedload(BookPublisher.books))
    )

    result = await session.execute(statement)

    publisher = result.unique().scalar_one_or_none()

    if publisher is None:
        logger.error(
            f"Failed to get book publisher with id {publisher_id} - publisher was not found"
        )
        return None

    return BookPublisherSchema.model_validate(publisher)


async def get_book_publisher_by_slug(
    session: AsyncSession, publisher_slug: str
) -> BookPublisherSchema | None:
    logger.info(f"Try to get book publisher {publisher_slug}")
    statement = (
        select(BookPublisher)
        .where(BookPublisher.slug == publisher_slug)
        .options(joinedload(BookPublisher.books))
    )

    result = await session.execute(statement)

    publisher = result.unique().scalar_one_or_none()

    if publisher is None:
        logger.error(
            f"Failed to get book publisher {publisher_slug} - publisher was not found"
        )
        return None

    return BookPublisherSchema.model_validate(publisher)


async def create_book_publisher(
    session: AsyncSession, data: BookPublisherCreate
) -> BookPublisher:
    logger.info(f"Try to create book publisher with data {data}")
    existing_publisher = await session.execute(
        select(BookPublisher).where(
            (BookPublisher.title == data.title) | (BookPublisher.slug == data.slug)
        )
    )

    if existing_publisher.scalar_one_or_none():
        logger.error(
            f"Failed to create publisher - publisher {data.title} already exists"
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Publisher with this title or slug already exists",
        )

    publisher = BookPublisher(
        title=data.title,
        slug=data.slug,
    )

    session.add(publisher)

    await session.commit()
    await session.refresh(publisher)

    return publisher


async def update_book_publisher(
    session: AsyncSession,
    publisher_id: int,
    data: BookPublisherUpdate | BookPublisherUpdatePublisher,
    partial: bool = False,
) -> BookPublisher | None:
    logger.info(f"Try to update book publisher {publisher_id} with data {data}")
    result = await session.execute(
        select(BookPublisher).where(BookPublisher.id == publisher_id)
    )

    publisher = result.scalar_one_or_none()

    if publisher is None:
        logger.error(f"Failed to update book publisher: {publisher_id} was not found")
        return None

    update_data = data.model_dump(exclude_unset=partial)

    for key, value in update_data.items():
        setattr(publisher, key, value)

    await session.commit()
    await session.refresh(publisher)

    return publisher


async def delete_book_publisher(
    session: AsyncSession,
    publisher_id: int,
) -> tuple[bool, BookPublisher | None]:

    logger.info(f"Try to delete book publisher with id {publisher_id}")
    result = await session.execute(
        select(BookPublisher).where(BookPublisher.id == publisher_id)
    )

    publisher = result.scalar_one_or_none()

    if publisher is None:
        logger.error(f"Failed to delete book publisher with id {publisher_id}")
        return False, None

    deleted_publisher = publisher

    await session.delete(publisher)
    await session.commit()

    return True, deleted_publisher
