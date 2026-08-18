import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import BookAuthors, db_helper
from .data import authors
from entities.book_authors.schema import (
    BookAuthorsSchema,
    BookAuthorsCreate,
    BookAuthorsUpdate,
    BookAuthorsUpdatePartial,
)


async def get_all_authors(
    session: AsyncSession, limit: int = 10, offset: int = 0
) -> list[BookAuthorsSchema]:
    statement = select(BookAuthors).order_by(BookAuthors.id).offset(offset).limit(limit)

    result = await session.execute(statement)
    authors = result.scalars().all()

    return [BookAuthorsSchema.model_validate(author) for author in authors]


async def create_author(
    session: AsyncSession, data: BookAuthorsCreate
) -> BookAuthorsSchema:
    new_author = BookAuthors(**data.model_dump())

    session.add(new_author)
    await session.commit()
    await session.refresh(new_author)

    return BookAuthorsSchema.model_validate(new_author)


async def get_author_by_id(session: AsyncSession, author_id: int) -> BookAuthors | None:
    statement = select(BookAuthors).where(BookAuthors.id == author_id)

    result = await session.execute(statement)
    author = result.scalar_one_or_none()

    if author is None:
        return None

    return author


async def update_author(
    session: AsyncSession, author_id: int, data: BookAuthorsUpdate
) -> BookAuthorsSchema | None:
    statement = select(BookAuthors).where(BookAuthors.id == author_id)

    result = await session.execute(statement)
    author = result.scalar_one_or_none()

    if author is None:
        return None

    for key, value in data.model_dump().items():
        setattr(author, key, value)

    await session.commit()
    await session.refresh(author)

    return BookAuthorsSchema.model_validate(author)


async def partial_update_author(
    session: AsyncSession, author_id: int, data: BookAuthorsUpdatePartial
):
    statement = select(BookAuthors).where(BookAuthors.id == author_id)
    result = await session.execute(statement)
    author = result.scalar_one_or_none()

    if author is None:
        return None

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(author, key, value)

    await session.commit()
    await session.refresh(author)

    return BookAuthorsSchema.model_validate(author)


async def delete_author(session: AsyncSession, author_id: int) -> bool:
    result = await session.execute(
        select(BookAuthors).where(BookAuthors.id == author_id)
    )
    author = result.scalar_one_or_none()

    if author is None:
        return False

    await session.delete(author)
    await session.commit()
    return True


async def seed_authors(session: AsyncSession):
    for author in authors:
        author_create = BookAuthorsCreate(**author)
        await create_author(session, author_create)
    print("Successfully")


async def main():
    async with db_helper.session_factory() as session:
        await seed_authors(session)
    pass


if __name__ == "__main__":
    asyncio.run(main())
