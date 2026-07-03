import asyncio
from datetime import date

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from entities.template_quotes.schema import (
    TemplateQuoteSchema,
    TemplateQuoteCreate,
    TemplateQuoteUpdate,
    TemplateQuoteUpdatePartial,
)

from core.models import TemplateQuote, db_helper
from .data import quotes


async def get_all_template_quotes(session: AsyncSession) -> list[TemplateQuoteSchema]:
    statement = select(TemplateQuote)

    result = await session.execute(statement)
    template_quotes = result.scalars().all()
    return [TemplateQuoteSchema.model_validate(quote) for quote in template_quotes]


async def create_template_quote(
    session: AsyncSession, data: TemplateQuoteCreate
) -> TemplateQuoteSchema:
    new_template_quote = TemplateQuote(**data.model_dump())

    session.add(new_template_quote)
    await session.commit()
    await session.refresh(new_template_quote)

    return TemplateQuoteSchema.model_validate(new_template_quote)


async def get_today_template_quote(session: AsyncSession) -> TemplateQuoteSchema | None:
    today = date.today()
    today_statement = select(TemplateQuote).where(TemplateQuote.last_shown_at == today)
    today_result = await session.execute(today_statement)
    current_quote = today_result.scalar_one_or_none()

    if current_quote:
        return TemplateQuoteSchema.model_validate(current_quote)

    statement = (
        select(TemplateQuote)
        .order_by(TemplateQuote.last_shown_at.asc().nullsfirst(), func.random())
        .limit(1)
    )

    result = await session.execute(statement)
    quote_to_show = result.scalar_one_or_none()

    if not quote_to_show:
        return None

    quote_to_show.last_shown_at = today
    await session.commit()
    await session.refresh(quote_to_show)

    return TemplateQuoteSchema.model_validate(quote_to_show)


async def get_quote_by_id(session: AsyncSession, quote_id: int) -> TemplateQuote | None:
    statement = select(TemplateQuote).where(TemplateQuote.id == quote_id)

    result = await session.execute(statement)
    quote = result.scalar_one_or_none()

    if quote is None:
        return None
    return quote


async def update_template_quote(
    session: AsyncSession, quote_id: int, data: TemplateQuoteUpdate
) -> TemplateQuoteSchema | None:

    statement = select(TemplateQuote).where(TemplateQuote.id == quote_id)

    result = await session.execute(statement)
    quote = result.scalar_one_or_none()

    if quote is None:
        return None

    for key, value in data.model_dump().items():
        setattr(quote, key, value)

    await session.commit()
    await session.refresh(quote)

    return TemplateQuoteSchema.model_validate(quote)


async def partial_update_template_quote(
    session: AsyncSession, quote_id: int, data: TemplateQuoteUpdatePartial
):
    statement = select(TemplateQuote).where(TemplateQuote.id == quote_id)
    result = await session.execute(statement)

    quote = result.scalar_one_or_none()

    if quote is None:
        return None

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(quote, key, value)

    await session.commit()
    await session.refresh(quote)

    return TemplateQuoteSchema.model_validate(quote)


async def delete_template_quote(session: AsyncSession, quote_id: int) -> bool:
    result = await session.execute(
        select(TemplateQuote).where(TemplateQuote.id == quote_id)
    )

    quote = result.scalar_one_or_none()

    if quote is None:
        return False

    await session.delete(quote)
    await session.commit()
    return True


async def seed_quotes(session: AsyncSession):
    for quote in quotes:
        quote_create = TemplateQuoteCreate(**quote)
        await create_template_quote(session, quote_create)
    print("Successfully")


async def main():
    async with db_helper.session_factory() as session:
        await seed_quotes(session)
    pass


if __name__ == "__main__":
    asyncio.run(main())
