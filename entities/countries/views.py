import json

from loguru import logger

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.redis_config import redis_client
from core.models import db_helper

from . import crud
from .schema import (
    CountrySchema,
    CountryCreate,
    CountryUpdate,
    CountryUpdatePartial,
    CountrySummarySchema,
)

router = APIRouter(tags=["Countries"])


async def invalidate_countries_cache():
    keys = []

    async for key in redis_client.scan_iter(match="countries:*"):
        keys.append(key)

    if keys:
        await redis_client.delete(*keys)


@router.get("/", response_model=list[CountrySchema])
async def get_all_countries_view(
    limit: int = Query(default=10, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    cache_key = f"countries:limit:{limit}:offset:{offset}"
    cached = await redis_client.get(cache_key)

    if cached:
        logger.info("Get all countries from Redis cache")
        return json.loads(cached)

    data = await crud.get_all_countries(session=session, limit=limit, offset=offset)
    serialized = [item.model_dump(mode="json") for item in data]

    await redis_client.set(
        cache_key, json.dumps(serialized, ensure_ascii=False), ex=300
    )

    logger.info("Return all countries")
    return data


@router.get("/{country_id}", response_model=CountrySchema)
async def get_country_by_id_view(
    country_id: int,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    cache_key = f"countries:{country_id}"
    cached = await redis_client.get(cache_key)

    if cached:
        logger.info(f"Get country {country_id} from Redis cache")
        return json.loads(cached)

    country = await crud.get_country_by_id(session, country_id)

    if country is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Country not found"
        )

    result = CountrySchema.model_validate(country)

    await redis_client.set(cache_key, result.model_dump_json(), ex=300)

    return result


@router.get("/{country_id}/summary", response_model=CountrySummarySchema)
async def get_country_summary_view(
    country_id: int,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    cache_key = f"countries:{country_id}:summary"
    cached = await redis_client.get(cache_key)

    if cached:
        logger.info(f"Get country summary {country_id} from Redis cache")
        return json.loads(cached)

    country = await crud.get_country_summary(session, country_id)

    if country is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Country not found"
        )

    result = country.model_dump(mode="json")
    await redis_client.set(cache_key, json.dumps(result, ensure_ascii=False), ex=300)

    return result


@router.get("/code/{country_code}", response_model=CountrySchema)
async def get_country_code_by_view(
    country_code: str,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    normalized_code = country_code.upper()
    cache_key = f"countries:code:{normalized_code}"

    cached = await redis_client.get(cache_key)

    if cached:
        logger.info(f"Get country {country_code} from Redis cache")
        return json.loads(cached)

    country = await crud.get_country_by_code(session, country_code)

    if country is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Country not found"
        )

    result = CountrySchema.model_validate(country)

    await redis_client.set(cache_key, result.model_dump_json(), ex=300)

    return result


@router.post("/", response_model=CountrySchema, status_code=status.HTTP_201_CREATED)
async def create_country_view(
    data: CountryCreate,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    country = await crud.create_country(session, data)
    await invalidate_countries_cache()
    logger.info("Create new country")

    return country


@router.put("/{country_id}", response_model=CountrySchema)
async def update_country_view(
    country_id: int,
    data: CountryUpdate,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    updated = await crud.update_country(session, country_id, data)

    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Country not found"
        )

    await invalidate_countries_cache()

    logger.info(f"Update country {country_id}")

    return updated


@router.patch("/{country_id}", response_model=CountrySchema)
async def partial_update_country_view(
    country_id: int,
    data: CountryUpdatePartial,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    updated = await crud.partial_update_country(session, country_id, data)

    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Country not found"
        )

    await invalidate_countries_cache()

    logger.info(f"Partially update country {country_id}")
    return updated


@router.delete("/{country_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_country_view(
    country_id: int,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    deleted = await crud.delete_country(session, country_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Country not found",
        )

    await invalidate_countries_cache()
    logger.info(f"Delete country {country_id}")
