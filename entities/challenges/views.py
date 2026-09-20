import json
from typing import Optional

from loguru import logger
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.redis_config import redis_client
from core.models import db_helper
from entities.challenges.schema import (
    ChallengeSchema,
    ChallengeCreate,
    ChallengeUpdatePartial,
    ChallengeWithDetailsSchema,
    ChallengeBookSchema,
    UserChallengeSchema,
    ChallengeWithParticipantsSummarySchema,
    SetWinnersSchema,
)

from . import crud

router = APIRouter(prefix="/challenges", tags=["Challenges"])


@router.get("/", response_model=list[ChallengeSchema])
async def get_all_challenges(
    limit: Optional[int] = Query(default=None, ge=1, le=100),
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    cache_key = f"challenges:all:limit:{limit}" if limit else "challenges:all"

    cached = await redis_client.get(cache_key)
    if cached:
        logger.info(f"Get all challenges with limit { limit } from Redis cache")
        return json.loads(cached)

    challenges = await crud.get_all_challenges(session=session, limit=limit)
    logger.info(f"Return all challenges with limit {limit} from db")

    await redis_client.set(
        cache_key, json.dumps([c.model_dump(mode="json") for c in challenges]), ex=600
    )

    return challenges


@router.get("/{challenge_id}")
async def get_challenge_by_id(
    challenge_id: int,
    with_details: bool = Query(default=False),
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    cache_key = f"challenges:id:{challenge_id}:details:{with_details}"

    cached = await redis_client.get(cache_key)

    if cached:
        logger.info(f"Get challenge {challenge_id} from Redis cache")
        return json.loads(cached)

    challenge = await crud.get_challenge_by_id(session, challenge_id, with_details)

    if not challenge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Challenge not found"
        )

    logger.info(f"Return challenge {challenge_id} from db")
    await redis_client.set(cache_key, challenge.model_dump_json(), ex=300)
    return challenge


@router.get("/by-slug/{slug}")
async def get_challenge_by_slug(
    slug: str,
    with_details: bool = Query(default=False),
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    cache_key = f"challenges:slug:{slug}:details:{with_details}"

    cached = await redis_client.get(cache_key)
    if cached:
        logger.info(f"Get challenge '{slug}' from Redis cache")
        return json.loads(cached)

    challenge = await crud.get_challenge_by_slug(
        session, slug, with_details=with_details
    )
    if not challenge:
        logger.error(f"Failed to get challenge '{slug}' - not found in db")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Challenge not found"
        )

    logger.info(f"Return challenge '{slug}' from db")
    await redis_client.set(cache_key, challenge.model_dump_json(), ex=300)
    return challenge


@router.post("/", response_model=ChallengeSchema, status_code=status.HTTP_201_CREATED)
async def create_challenge(
    data: ChallengeCreate,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    new_challenge = await crud.create_challenge(session, data)
    logger.info(f"Created challenge with title '{data.title}'")

    await redis_client.delete("challenges:all")
    return new_challenge


@router.patch("/{challenge_id}", response_model=ChallengeSchema)
async def update_challenge(
    challenge_id: int,
    data: ChallengeUpdatePartial,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    updated_challenge = await crud.update_challenge(
        session, challenge_id, data, partial=True
    )

    await redis_client.delete(f"challenges:id:{challenge_id}:details:False")
    await redis_client.delete(f"challenges:id:{challenge_id}:details:True")
    await redis_client.delete(f"challenges:slug:{updated_challenge.slug}:details:False")
    await redis_client.delete(f"challenges:slug:{updated_challenge.slug}:details:True")
    await redis_client.delete("challenges:all")

    return updated_challenge


@router.delete("/{challenge_id}", status_code=status.HTTP_200_OK)
async def delete_challenge(
    challenge_id: int,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    challenge = await crud.get_challenge_by_id(session, challenge_id)
    if not challenge:
        logger.error(f"Failed to delete challenge {challenge_id} - not found in db")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Challenge not found"
        )

    await crud.delete_challenge(session, challenge_id)

    await redis_client.delete(f"challenges:id:{challenge_id}:details:False")
    await redis_client.delete(f"challenges:id:{challenge_id}:details:True")
    await redis_client.delete(f"challenges:slug:{challenge.slug}:details:False")
    await redis_client.delete(f"challenges:slug:{challenge.slug}:details:True")
    await redis_client.delete("challenges:all")

    return {"ok": True}


@router.get("/{challenge_id}/books", response_model=list[ChallengeBookSchema])
async def get_challenge_books(
    challenge_id: int,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    books = await crud.get_challenge_books(session, challenge_id)
    return [ChallengeBookSchema.model_validate(b) for b in books]


@router.get("/{challenge_id}/participants", response_model=list[UserChallengeSchema])
async def get_challenge_participants(
    challenge_id: int,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    participants = await crud.get_challenge_participants(session, challenge_id)
    return [UserChallengeSchema.model_validate(p) for p in participants]


@router.get("/by-book/{book_id}", response_model=list[ChallengeSchema])
async def get_challenges_by_book(
    book_id: int,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    return await crud.get_challenges_by_book_id(session, book_id)


@router.get("/user/{username}", response_model=list[ChallengeSchema])
async def get_challenges_by_user(
    username: str,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    cache_key = f"challenges:user:{username}"

    cached = await redis_client.get(cache_key)
    if cached:
        logger.info(f"Get challenges for user {username} from Redis cache")
        return json.loads(cached)

    challenges = await crud.get_challenges_by_username(session, username)

    await redis_client.set(
        cache_key,
        json.dumps([c.model_dump(mode="json") for c in challenges]),
        ex=300,
    )
    return challenges


@router.post("/{challenge_id}/join/{username}")
async def join_challenge(
    challenge_id: int,
    username: str,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    assoc = await crud.join_challenge(session, username, challenge_id)

    await redis_client.delete(f"challenges:user:{username}")
    await redis_client.delete(f"challenges:id:{challenge_id}:details:True")

    return {
        "ok": True,
        "challenge_id": challenge_id,
        "username": username,
        "joined_at": assoc.joined_at.isoformat(),
    }


@router.delete("/{challenge_id}/leave/{username}")
async def leave_challenge(
    challenge_id: int,
    username: str,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    left = await crud.leave_challenge(session, username, challenge_id)

    if not left:
        logger.error(
            f"Failed user {username} to leave challenge {challenge_id} - not participating"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not participating in this challenge",
        )

    await redis_client.delete(f"challenges:user:{username}")
    await redis_client.delete(f"challenges:id:{challenge_id}:details:True")

    return {"ok": True}


@router.get(
    "/{challenge_id}/summary",
    response_model=ChallengeWithParticipantsSummarySchema,
)
async def get_challenge_summary(
    challenge_id: int | str,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    cache_key = f"challenges:summary:{challenge_id}"

    cached = await redis_client.get(cache_key)
    if cached:
        logger.info(f"Get challenge summary {challenge_id} from Redis cache")
        return json.loads(cached)

    summary = await crud.get_challenge_with_participants_summary(session, challenge_id)

    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Challenge not found"
        )

    logger.info(f"Return challenge summary {challenge_id} from db")
    await redis_client.set(cache_key, summary.model_dump_json(), ex=300)

    return summary


@router.post(
    "/{challenge_id}/set-winners",
    response_model=ChallengeWithDetailsSchema,
    status_code=status.HTTP_200_OK,
)
async def set_challenge_winners(
    challenge_id: int,
    payload: SetWinnersSchema,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    logger.info(f"Received request to set winners for challenge_id={challenge_id}")

    updated_challenge = await crud.set_challenge_winners(
        session=session,
        challenge_id=challenge_id,
        winner_user_ids=payload.winners_ids,
        super_winner_user_ids=payload.super_winners_ids,
    )

    await redis_client.delete(f"challenges:id:{challenge_id}:details:False")
    await redis_client.delete(f"challenges:id:{challenge_id}:details:True")
    await redis_client.delete(f"challenges:slug:{updated_challenge.slug}:details:False")
    await redis_client.delete(f"challenges:slug:{updated_challenge.slug}:details:True")
    await redis_client.delete(f"challenges:summary:{challenge_id}")
    await redis_client.delete(f"challenges:summary:{updated_challenge.slug}")
    await redis_client.delete("challenges:all")

    for user_id in set(payload.winners_ids + payload.super_winners_ids):
        await redis_client.delete(f"challenges:user:{user_id}")

    return updated_challenge
