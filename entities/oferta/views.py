import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.redis_config import redis_client
from core.models import db_helper
from entities.oferta.schema import OfertaSchema, OfertaCreate
from . import crud
from .crud import create_or_update_oferta

router = APIRouter(tags=["Oferta"])


@router.get("/")
async def get_oferta(
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    cache_key = "oferta"

    cached = await redis_client.get(cache_key)

    if cached:
        return json.loads(cached)

    data = await crud.get_last_oferta(session)

    if not data:
        return {}
    await redis_client.set(cache_key, json.dumps(data.model_dump()), ex=300)
    return data


@router.put("/")
async def update_oferta(
    oferta_data: OfertaCreate,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    await redis_client.delete("oferta")

    return await create_or_update_oferta(
        session=session,
        oferta_data=oferta_data,
    )


@router.delete("/")
async def delete_oferta(
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):

    await redis_client.delete("oferta")

    deleted = await crud.delete_oferta(session)
    if deleted:
        return {"ok": True}
    return {"ok": False}
