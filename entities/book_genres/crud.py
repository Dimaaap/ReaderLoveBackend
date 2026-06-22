from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import BookGenres
from entities.book_genres.schema import (
    BookGenreSchema
)


async def get_all_genres(session: AsyncSession) -> list[BookGenreSchema]:
    statement = select(BookGenres)

    result = await session.execute(statement)
    genres = result.scalars().all()

    return [BookGenreSchema.model_validate(genre) for genre in genres]