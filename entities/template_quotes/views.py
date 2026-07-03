import json
from datetime import datetime, time

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.redis_config import redis_client
from core.models import db_helper
from entities.template_quotes.schema import (
    TemplateQuoteSchema,
    TemplateQuoteCreate,
    TemplateQuoteUpdatePartial,
)
from . import crud

router = APIRouter(tags=["Template Quotes"])


@router.get("/", response_model=list[TemplateQuoteSchema])
async def get_all(session: AsyncSession = Depends(db_helper.scoped_session_dependency)):
    cache_key = "template_quotes:all"

    cached = await redis_client.get(cache_key)

    if cached:
        return json.loads(cached)

    data = await crud.get_all_template_quotes(session)
    result = [TemplateQuoteSchema.model_validate(quote) for quote in data]

    await redis_client.set(
        cache_key, json.dumps([item.model_dump() for item in data]), ex=300
    )

    return result


@router.get("/today")
async def get_today_quote(
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    cache_key = "template_quotes:today"
    cached = await redis_client.get(cache_key)

    if cached:
        return json.loads(cached)

    data = await crud.get_today_template_quote(session)

    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Today`s quote is not found"
        )

    now = datetime.now()
    tomorrow = datetime.combine(now.date(), time.max)
    seconds_until_midnight = int((tomorrow - now).total_seconds())

    ttl = max(seconds_until_midnight, 300)

    await redis_client.set(cache_key, data.model_dump_json(), ex=ttl)

    return data


@router.get("/{quote_id}")
async def get_template_quote_by_id(
    quote_id: int, session: AsyncSession = Depends(db_helper.scoped_session_dependency)
):
    cache_key = f"template_quotes:{quote_id}"

    cached = await redis_client.get(cache_key)

    if cached:
        return json.loads(cached)

    data = await crud.get_quote_by_id(session, quote_id)

    if data:
        result = TemplateQuoteSchema.model_validate(data)
        await redis_client.set(cache_key, result.model_dump_json(), ex=300)

        return result
    return data


@router.post("/", response_model=TemplateQuoteCreate, status_code=201)
async def create_template_quote_view(
    data: TemplateQuoteCreate,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    quote = await crud.create_template_quote(session, data)

    await redis_client.delete("template_quotes:all")
    return quote


@router.patch("/{quote_id}", response_model=TemplateQuoteUpdatePartial)
async def update_template_quote_view(
    quote_id: int,
    data: TemplateQuoteUpdatePartial,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    updated = await crud.partial_update_template_quote(session, quote_id, data)

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Template quote is not found"
        )

    await redis_client.delete("template_quotes:all")

    today_cached = await redis_client.get("template_quotes:today")
    if today_cached:
        today_quote_data = json.loads(today_cached)
        if today_quote_data.get("id") == quote_id:
            await redis_client.delete(
                f"template_quotes:{quote_id}", "template_quotes:today"
            )
        else:
            await redis_client.delete(f"template_quotes:{quote_id}")
    else:
        await redis_client.delete(f"template_quotes:{quote_id}")
