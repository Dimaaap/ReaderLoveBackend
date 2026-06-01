import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.redis_config import redis_client
from core.models import db_helper
from entities.social_links.schema import SocialLinkSchema

from .crud import *

router = APIRouter(tags=["Social Links"])


@router.get("/", response_model=list[SocialLinkSchema])
async def get_all(
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    cache_key = "social_links:all"

    cached = await redis_client.get(cache_key)

    if cached:
        return json.loads(cached)

    data = await get_all_social_links(session)
    result = [SocialLinkSchema.model_validate(item) for item in data]

    await redis_client.set(
        cache_key, json.dumps([item.model_dump() for item in data]), ex=300
    )

    return result
