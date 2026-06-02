import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.redis_config import redis_client
from core.models import db_helper
from entities.social_links.schema import SocialLinkSchema

from . import crud

router = APIRouter(tags=["Social Links"])


@router.get("/", response_model=list[SocialLinkSchema])
async def get_all(
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    cache_key = "social_links:all"

    cached = await redis_client.get(cache_key)

    if cached:
        return json.loads(cached)

    data = await crud.get_all_social_links(session)
    result = [SocialLinkSchema.model_validate(item) for item in data]

    await redis_client.set(
        cache_key, json.dumps([item.model_dump() for item in data]), ex=300
    )

    return result


@router.get("/{social_link_id}")
async def get_social_link_by_id(
    social_link_id: int,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    cache_key = f"social_links:{social_link_id}"

    cached = await redis_client.get(cache_key)

    if cached:
        return json.loads(cached)

    data = await crud.get_social_link_by_id(session, social_link_id)

    if data:
        await redis_client.set(cache_key, SocialLinkSchema.model_validate(data), ex=300)

    return data
