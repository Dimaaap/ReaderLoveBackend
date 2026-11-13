import asyncio

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from core.models import BookAuthors, db_helper
from .data import authors
from .schema import (
    BookAuthorsSchema,
    BookAuthorsCreate,
    BookAuthorsUpdate,
    BookAuthorsUpdatePartial,
)


async def get_all_authors(
    session: AsyncSession,
    limit: int = 10,
    offset: int = 0,
) -> list[BookAuthorsSchema]:
    statement = (
        select(BookAuthors)
        .options(selectinload(BookAuthors.country))
        .order_by(BookAuthors.id)
        .offset(offset)
        .limit(limit)
    )

    result = await session.execute(statement)
    authors_list = result.scalars().all()

    logger.info("Get all book authors data")

    return [BookAuthorsSchema.model_validate(author) for author in authors_list]


async def get_author_by_id(
    session: AsyncSession,
    author_id: int,
) -> BookAuthorsSchema | None:
    statement = (
        select(BookAuthors)
        .options(selectinload(BookAuthors.country))
        .where(BookAuthors.id == author_id)
    )

    result = await session.execute(statement)
    author = result.scalar_one_or_none()

    if author is None:
        logger.warning(f"Author with id {author_id} not found")
        return None

    return BookAuthorsSchema.model_validate(author)


async def create_author(
    session: AsyncSession,
    data: BookAuthorsCreate,
) -> BookAuthorsSchema:
    new_author = BookAuthors(**data.model_dump())

    logger.info(f"Try to create author {data.first_name} {data.last_name}")

    session.add(new_author)
    await session.commit()

    return await get_author_by_id(session, new_author.id)


async def update_author(
    session: AsyncSession,
    author_id: int,
    data: BookAuthorsUpdate,
) -> BookAuthorsSchema | None:
    result = await session.execute(
        select(BookAuthors).where(BookAuthors.id == author_id)
    )
    author = result.scalar_one_or_none()

    if author is None:
        return None

    for key, value in data.model_dump().items():
        setattr(author, key, value)

    await session.commit()

    return await get_author_by_id(session, author_id)


async def partial_update_author(
    session: AsyncSession,
    author_id: int,
    data: BookAuthorsUpdatePartial,
) -> BookAuthorsSchema | None:
    result = await session.execute(
        select(BookAuthors).where(BookAuthors.id == author_id)
    )
    author = result.scalar_one_or_none()

    if author is None:
        return None

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(author, key, value)

    await session.commit()

    return await get_author_by_id(session, author_id)


async def delete_author(
    session: AsyncSession,
    author_id: int,
) -> bool:
    result = await session.execute(
        select(BookAuthors).where(BookAuthors.id == author_id)
    )
    author = result.scalar_one_or_none()

    if author is None:
        logger.warning(f"Author with id {author_id} not found")
        return False

    await session.delete(author)
    await session.commit()

    logger.info(f"Deleted author with id {author_id}")
    return True


async def seed_authors(session: AsyncSession):
    session.add_all([BookAuthors(**author) for author in authors])

    await session.commit()
    logger.info("Successfully seeded authors")


async def main():
    async with db_helper.session_factory() as session:
        await seed_authors(session)


if __name__ == "__main__":
    asyncio.run(main())
