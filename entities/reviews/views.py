import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.redis_config import redis_client
from core.models import db_helper
from entities.reviews.schema import ReviewSchema, ReviewCreate, ReviewUpdatePartial
from . import crud

router = APIRouter(tags=["Reviews"])


@router.get("/", response_model=list[ReviewSchema])
async def get_all(session: AsyncSession = Depends(db_helper.scoped_session_dependency)):
    cache_key = "reviews:all"

    cached = await redis_client.get(cache_key)

    if cached:
        return json.loads(cached)

    data = await crud.get_all_reviews(session)
    result = [ReviewSchema.model_validate(review) for review in data]

    await redis_client.set(
        cache_key, json.dumps([item.model_dump() for item in data]), ex=300
    )

    return result


@router.get("/{review_id}")
async def get_review_by_id(
    review_id: int, session: AsyncSession = Depends(db_helper.scoped_session_dependency)
):
    cache_key = f"reviews:{review_id}"

    cached = await redis_client.get(cache_key)

    if cached:
        return json.loads(cached)

    data = await crud.get_review_by_id(session, review_id)

    if data:
        result = ReviewSchema.model_validate(data)

        await redis_client.set(cache_key, result.model_dump_json(), ex=300)

        return result
    return data


@router.post("/", response_model=ReviewCreate, status_code=201)
async def create_review_view(
    data: ReviewCreate,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    review = await crud.create_review(session, data)

    await redis_client.delete("reviews:all")
    return review


@router.delete("/{review_id}")
async def delete_review_by_id_view(
    review_id: int, session: AsyncSession = Depends(db_helper.scoped_session_dependency)
):
    deleted = await crud.delete_review(session, review_id)

    if deleted:
        try:
            await redis_client.delete(f"reviews:{review_id}")
            await redis_client.delete("reviews:all")
        except Exception:
            return
    return {"ok": True}


@router.patch("/{review_id}", response_model=ReviewUpdatePartial)
async def update_review_view(
    review_id: int,
    data: ReviewUpdatePartial,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    updated = await crud.partial_update_review(session, review_id, data)

    if not updated:
        raise HTTPException(status_code=404, detail="Review is not found")

    await redis_client.delete("reviews:all")
    await redis_client.delete(f"reviews:{review_id}")

    return updated
