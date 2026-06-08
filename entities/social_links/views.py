import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.redis_config import redis_client
from core.models import db_helper
from entities.social_links.schema import (
    SocialLinkSchema,
    SocialLinkCreate,
    SocialLinkUpdatePartial,
)

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
        result = SocialLinkSchema.model_validate(data)

        await redis_client.set(
            cache_key,
            result.model_dump_json(),
            ex=300,
        )

        return result
    return data


@router.post("/", response_model=SocialLinkCreate, status_code=201)
async def create_social_link_view(
    data: SocialLinkCreate,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    social_link = await crud.create_social_link(session, data)

    await redis_client.delete("social_links:all")
    return social_link


@router.delete("/{social_link_id}")
async def delete_social_link_by_id_view(
    social_link_id: int,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    deleted = await crud.delete_social_link(session, social_link_id)

    if deleted:
        try:
            await redis_client.delete(f"social_links:{social_link_id}")
            await redis_client.delete("social_links:all")
        except Exception as e:
            return
    return {"ok": True}


@router.patch("/{social_link_id}", response_model=SocialLinkUpdatePartial)
async def update_social_link_view(
    social_link_id: int,
    data: SocialLinkUpdatePartial,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    updated = await crud.partial_update_social_link(session, social_link_id, data)

    if not updated:
        raise HTTPException(status_code=404, detail="Social link is not found")

    await redis_client.delete("social_links:all")
    await redis_client.delete(f"social_links:{social_link_id}")

    return updated
