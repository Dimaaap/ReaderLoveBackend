import asyncio

from sqlalchemy import select, func, distinct
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from core.models import Country, db_helper, BookAuthors, Book, UserBookAssociation, User
from .schema import (
    CountrySchema,
    CountryCreate,
    CountryUpdate,
    CountryUpdatePartial,
    CountrySummarySchema,
    CountryGeographySchema,
)


async def get_all_countries(
    session: AsyncSession, limit: int = 10, offset: int = 0
) -> list[CountrySchema]:
    statement = select(Country).order_by(Country.name).offset(offset).limit(limit)

    result = await session.execute(statement)
    countries = result.scalars().all()

    logger.info("Get all countries data")

    return [CountrySchema.model_validate(country) for country in countries]


async def create_country(session: AsyncSession, data: CountryCreate) -> CountrySchema:
    new_country = Country(**data.model_dump())

    logger.info(f"Try to create country {data.name}")

    session.add(new_country)
    await session.commit()
    await session.refresh(new_country)

    return CountrySchema.model_validate(new_country)


async def get_country_by_id(session: AsyncSession, country_id: int) -> Country | None:
    statement = select(Country).where(Country.id == country_id)

    logger.info(f"Try to get country with id {country_id}")
    result = await session.execute(statement)
    country = result.scalar_one_or_none()

    if country is None:
        logger.error(f"Error to get country with id {country_id}")
        return None

    return country


async def get_country_by_code(
    session: AsyncSession, country_code: str
) -> Country | None:
    statement = select(Country).where(Country.code == country_code.upper())

    result = await session.execute(statement)
    return result.scalar_one_or_none()


async def update_country(
    session: AsyncSession, country_id: int, data: CountryUpdate
) -> CountrySchema | None:
    statement = select(Country).where(Country.id == country_id)

    result = await session.execute(statement)
    country = result.scalar_one_or_none()

    if country is None:
        return None

    for key, value in data.model_dump().items():
        setattr(country, key, value)

    await session.commit()
    await session.refresh(country)

    return CountrySchema.model_validate(country)


async def partial_update_country(
    session: AsyncSession, country_id: int, data: CountryUpdatePartial
) -> CountrySchema | None:
    statement = select(Country).where(Country.id == country_id)

    result = await session.execute(statement)
    country = result.scalar_one_or_none()

    if country is None:
        return None

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(country, key, value)

    await session.commit()
    await session.refresh(country)

    return CountrySchema.model_validate(country)


async def delete_country(session: AsyncSession, country_id: int) -> bool:
    result = await session.execute(select(Country).where(Country.id == country_id))

    country = result.scalar_one_or_none()
    logger.info(f"Try to delete country with id {country_id}")

    if country is None:
        logger.error(f"Error to delete country with id {country_id}")
        return False

    await session.delete(country)
    await session.commit()

    return True


async def get_country_summary(
    session: AsyncSession, country_id: int
) -> CountrySummarySchema | None:
    statement = (
        select(
            Country,
            func.count(Country.authors.property.mapper.class_.id).label(
                "authors_count"
            ),
        )
        .outerjoin(Country.authors)
        .where(Country.id == country_id)
        .group_by(Country.id)
    )

    result = await session.execute(statement)
    row = result.one_or_none()

    if row is None:
        return None

    country, authors_count = row
    return CountrySummarySchema(
        **CountrySchema.model_validate(country).model_dump(),
        authors_count=authors_count,
    )


async def get_user_reading_geography(
    session: AsyncSession, username: str, book_status: str | None = None
) -> list[CountryGeographySchema]:
    statement = (
        select(
            Country,
            func.count(distinct(BookAuthors.id)).label("authors_count"),
            func.count(distinct(Book.id)).label("books_count"),
        )
        .select_from(UserBookAssociation)
        .join(Book, UserBookAssociation.book_id == Book.id)
        .join(Book.authors)
        .join(Country, BookAuthors.country_id == Country.id)
        .join(User, UserBookAssociation.user_id == User.id)
        .where(User.username == username)
        .group_by(Country.id)
        .order_by(func.count(distinct(Book.id)).desc(), Country.name)
    )

    if book_status and book_status != "all":
        statement = statement.where(UserBookAssociation.status == book_status)

    result = await session.execute(statement)
    rows = result.all()

    return [
        CountryGeographySchema(
            **CountrySchema.model_validate(country).model_dump(),
            authors_count=authors_count,
            books_count=books_count,
        )
        for country, authors_count, books_count in rows
    ]
