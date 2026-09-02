import asyncio

from loguru import logger
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import BookGenres, Book
from core.models import db_helper
from .data import genres
from entities.book_genres.schema import (
    BookGenreSchema,
    BookGenreCreate,
    BookGenreUpdate,
    BookGenreUpdatePartial,
)


async def get_all_genres(
    session: AsyncSession, limit: int = 10, offset: int = 0
) -> list[BookGenreSchema]:
    statement = select(BookGenres).order_by(BookGenres.id).offset(offset).limit(limit)
    logger.info("Get all book genres")
    result = await session.execute(statement)
    genres = result.scalars().all()

    return [BookGenreSchema.model_validate(genre) for genre in genres]


async def create_genre(session: AsyncSession, data: BookGenreCreate) -> BookGenreSchema:
    new_genre = BookGenres(**data.model_dump())
    logger.info(f"Try to create new genre - {data.title}")
    session.add(new_genre)
    await session.commit()
    await session.refresh(new_genre)

    return BookGenreSchema.model_validate(new_genre)


async def get_genre_by_id(session: AsyncSession, id: int) -> BookGenres | None:
    statement = select(BookGenres).where(BookGenres.id == id)

    result = await session.execute(statement)
    genre = result.scalar_one_or_none()
    logger.info(f"Try to get book genre with id {id}")

    if genre is None:
        logger.error(f"Failed to get book genre with id {id}")
        return None
    return genre


async def get_genre_by_slug(
    session: AsyncSession, genre_slug: str
) -> BookGenres | None:
    statement = (
        select(BookGenres)
        .where(BookGenres.slug == genre_slug)
        .options(selectinload(BookGenres.books).selectinload(Book.authors))
    )

    result = await session.execute(statement)
    genre = result.scalar_one_or_none()
    logger.info(f"Try to get book genre by slug {genre_slug}")

    if genre is None:
        logger.error(f"Error to get book genre by slug {genre_slug}")
        return None

    return genre


async def update_genre(
    session: AsyncSession, genre_id: int, data: BookGenreUpdate
) -> BookGenreSchema | None:

    statement = select(BookGenres).where(BookGenres.id == genre_id)

    result = await session.execute(statement)
    genre = result.scalar_one_or_none()

    if genre is None:
        return None

    for key, value in data.model_dump().items():
        setattr(genre, key, value)

    await session.commit()
    await session.refresh(genre)

    return BookGenreSchema.model_validate(genre)


async def partial_update_genre(
    session: AsyncSession, genre_id: int, data: BookGenreUpdatePartial
):
    logger.info(f"Try to update book genre {genre_id} with data: {data}")
    statement = select(BookGenres).where(BookGenres.id == genre_id)
    result = await session.execute(statement)
    genre = result.scalar_one_or_none()

    if genre is None:
        logger.error(f"Failed to update book genre {genre_id}")
        return None

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(genre, key, value)

    await session.commit()
    await session.refresh(genre)

    return BookGenreSchema.model_validate(genre)


async def delete_genre(session: AsyncSession, genre_id: int) -> bool:
    result = await session.execute(select(BookGenres).where(BookGenres.id == genre_id))

    genre = result.scalar_one_or_none()
    logger.info(f"Try to delete book genre with id {genre_id}")

    if genre is None:
        logger.error(
            f"Failed to delete book genre with id {genre_id} - genre not found"
        )
        return False

    await session.delete(genre)
    await session.commit()
    return True, genre


async def seed_genres(session: AsyncSession):
    for genre in genres:
        genre_create = BookGenreCreate(**genre)
        await create_genre(session, genre_create)
    print("Successfully")


async def main():
    async with db_helper.session_factory() as session:
        await seed_genres(session)
    pass


if __name__ == "__main__":
    asyncio.run(main())
