from datetime import datetime, timezone

from loguru import logger
from fastapi import status, HTTPException
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.models import Challenge, UserChallenge, ChallengeBook, User, Book
from entities.challenges.schema import (
    ChallengeSchema,
    ChallengeCreate,
    ChallengeUpdate,
    ChallengeUpdatePartial,
    ChallengeWithDetailsSchema,
    ChallengeWithParticipantsSummarySchema,
    ParticipantPreviewSchema,
)


async def get_all_challenges(
    session: AsyncSession, limit: int | None = None
) -> list[ChallengeSchema]:
    logger.info(f"Try to get all challenges with params: limit={limit}")
    statement = (
        select(Challenge)
        .options(selectinload(Challenge.winners), selectinload(Challenge.super_winners))
        .order_by(desc(Challenge.created_at))
    )

    if limit is not None:
        statement = statement.limit(limit)

    result = await session.execute(statement)
    challenges = result.scalars().all()

    return [ChallengeSchema.model_validate(challenge) for challenge in challenges]


async def get_challenge_by_id(
    session: AsyncSession, challenge_id: int, with_details: bool = False
) -> ChallengeWithDetailsSchema | ChallengeSchema | None:
    logger.info(
        f"Try to get challenge with id {challenge_id} (with_details={with_details})"
    )

    statement = (
        select(Challenge)
        .where(Challenge.id == challenge_id)
        .options(
            selectinload(Challenge.winners),
            selectinload(Challenge.super_winners),
        )
    )

    if with_details:
        statement = statement.options(
            selectinload(Challenge.challenge_books).selectinload(ChallengeBook.book),
            selectinload(Challenge.participants).selectinload(UserChallenge.user),
        )

    result = await session.execute(statement)
    challenge = result.scalar_one_or_none()

    if not challenge:
        logger.error(
            f"Failed to get challenge with id { challenge_id } - not found in db"
        )
        return None

    if with_details:
        return ChallengeWithDetailsSchema.model_validate(challenge)

    return ChallengeSchema.model_validate(challenge)


async def get_challenge_by_slug(
    session: AsyncSession, slug: str, with_details: bool = False
) -> ChallengeWithDetailsSchema | ChallengeSchema | None:
    logger.info(
        f"Try to get challenge with slug '{slug}' (with_details={with_details})"
    )

    statement = (
        select(Challenge)
        .where(Challenge.slug == slug)
        .options(
            selectinload(Challenge.winners),
            selectinload(Challenge.super_winners),
        )
    )

    if with_details:
        statement = statement.options(
            selectinload(Challenge.challenge_books).selectinload(ChallengeBook.book),
            selectinload(Challenge.participants).selectinload(UserChallenge.user),
        )

    result = await session.execute(statement)
    challenge = result.scalar_one_or_none()

    if not challenge:
        logger.error(f"Failed to get challenge with slug '{slug}' - not found in db")
        return None

    if with_details:
        return ChallengeWithDetailsSchema.model_validate(challenge)

    return ChallengeSchema.model_validate(challenge)


async def create_challenge(
    session: AsyncSession, data: ChallengeCreate
) -> ChallengeSchema:
    logger.info(f"Try to create challenge with title '{ data.title }'")

    existing_statement = select(Challenge.id).where(Challenge.slug == data.slug)
    existing_res = await session.execute(existing_statement)

    if existing_res.scalar_one_or_none():
        logger.error(f"Challenge with slug '{data.slug}' already exists")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Челендж із slug '{ data.slug }' вже існує",
        )

    challenge_data = data.model_dump()
    challenge = Challenge(**challenge_data)

    session.add(challenge)
    await session.commit()
    await session.refresh(challenge)

    logger.info(f"Successfully created challenge with id { challenge.id }")
    return ChallengeSchema.model_validate(challenge)


async def update_challenge(
    session: AsyncSession,
    challenge_id: int,
    data: ChallengeUpdate | ChallengeUpdatePartial,
    partial: bool = False,
) -> ChallengeSchema:
    logger.info(f"Try to update challenge {challenge_id}")

    statement = select(Challenge).where(Challenge.id == challenge_id)
    result = await session.execute(statement)
    challenge = result.scalar_one_or_none()

    if not challenge:
        logger.error(f"Failed to update challenge { challenge_id } - not found")
        raise HTTPException(
            status_code=status.HTTP_404_BAD_REQUEST, detail="Челендж не знайдено"
        )

    update_data = data.model_dump(exclude_unset=partial)

    for key, value in update_data.items():
        setattr(challenge, key, value)

    await session.commit()
    await session.refresh(challenge)

    logger.info(f"Successfully updated challenge {challenge_id}")
    return ChallengeSchema.model_validate(challenge)


async def delete_challenge(session: AsyncSession, challenge_id: int) -> bool:
    logger.info(f"Try to delete challenge with id {challenge_id}")

    statement = select(Challenge).where(Challenge.id == challenge_id)
    result = await session.execute(statement)
    challenge = result.scalar_one_or_none()

    if not challenge:
        logger.error(f"Failed to delete challenge { challenge_id } - not found")
        return False

    await session.delete(challenge)
    await session.commit()
    logger.info(f"Successfully deleted challenge with id { challenge_id }")
    return True


async def get_challenge_books(
    session: AsyncSession, challenge_id: int
) -> list[ChallengeBook]:
    logger.info(f"Get books for challenge { challenge_id }")

    statement = (
        select(ChallengeBook)
        .where(ChallengeBook.challenge_id == challenge_id)
        .options(
            selectinload(ChallengeBook.book).options(
                selectinload(Book.authors), selectinload(Book.genres)
            )
        )
    )

    result = await session.execute(statement)
    return list(result.scalars().all())


async def get_challenge_participants(
    session: AsyncSession, challenge_id: int
) -> list[UserChallenge]:
    logger.info(f"Get participants for challenge { challenge_id }")

    statement = (
        select(UserChallenge)
        .where(UserChallenge.challenge_id == challenge_id)
        .options(selectinload(UserChallenge.user))
    )
    result = await session.execute(statement)
    return list(result.scalars().all())


async def get_challenges_by_book_id(
    session: AsyncSession, book_id: int
) -> list[ChallengeSchema]:
    logger.info(f"Get challenges containing book_id { book_id }")

    statement = (
        select(Challenge)
        .join(ChallengeBook, Challenge.id == ChallengeBook.challenge_id)
        .where(ChallengeBook.book_id == book_id)
        .options(
            selectinload(Challenge.winners),
            selectinload(Challenge.super_winners),
        )
        .order_by(desc(Challenge.created_at))
    )

    result = await session.execute(statement)
    challenges = result.scalars().all()
    return [ChallengeSchema.model_validate(challenge) for challenge in challenges]


async def get_challenges_by_username(
    session: AsyncSession, username: str
) -> list[ChallengeSchema]:
    logger.info(f"Get challenges for user { username }")

    statement = (
        select(Challenge)
        .join(UserChallenge, Challenge.id == UserChallenge.challenge_id)
        .join(User, UserChallenge.user_id == User.id)
        .where(User.username == username)
        .options(
            selectinload(Challenge.winners),
            selectinload(Challenge.super_winners),
        )
        .order_by(desc(Challenge.created_at))
    )

    result = await session.execute(statement)
    challenges = result.scalars().all()

    return [ChallengeSchema.model_validate(challenge) for challenge in challenges]


async def join_challenge(
    session: AsyncSession, username: str, challenge_id: int
) -> UserChallenge:
    logger.info(f"User { username } join challenge { challenge_id }")

    user_statement = select(User.id).where(User.username == username)
    user_result = await session.execute(user_statement)
    user_id = user_result.scalar_one_or_none()

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    associated_statement = select(UserChallenge).where(
        UserChallenge.user_id == user_id, UserChallenge.challenge_id == challenge_id
    )

    associated_result = await session.execute(associated_statement)
    associated = associated_result.scalar_one_or_none()

    if associated:
        return associated

    new_associated = UserChallenge(
        user_id=user_id, challenge_id=challenge_id, joined_at=datetime.now(timezone.utc)
    )

    session.add(new_associated)
    await session.commit()
    await session.refresh(new_associated)

    return new_associated


async def leave_challenge(
    session: AsyncSession, username: str, challenge_id: int
) -> bool:
    logger.info(f"User { username } leaves challenge { challenge_id }")

    statement = (
        select(UserChallenge)
        .join(User, UserChallenge.user_id == User.id)
        .where(User.username == username, UserChallenge.challenge_id == challenge_id)
    )

    result = await session.execute(statement)
    assoc = result.scalar_one_or_none()

    if assoc:
        await session.delete(assoc)
        await session.commit()
        return True
    return False


async def get_challenge_with_participants_summary(
    session: AsyncSession, challenge_id_or_slug: int | str
) -> ChallengeWithParticipantsSummarySchema | None:
    logger.info(
        f"Get challenge summary for '{challenge_id_or_slug}' with participants count"
    )

    if isinstance(challenge_id_or_slug, int) or (
        isinstance(challenge_id_or_slug, str) and challenge_id_or_slug.isdigit()
    ):
        statement = select(Challenge).where(Challenge.id == int(challenge_id_or_slug))
    else:
        statement = select(Challenge).where(
            (Challenge.id == challenge_id_or_slug)
            | (Challenge.slug == challenge_id_or_slug)
        )

    statement = statement.options(
        selectinload(Challenge.winners), selectinload(Challenge.super_winners)
    )
    res = await session.execute(statement)
    challenge = res.scalar_one_or_none()

    if not challenge:
        return None

    count_statement = select(func.count(UserChallenge.user_id)).where(
        UserChallenge.challenge_id == challenge.id
    )

    count_res = await session.execute(count_statement)
    total_participants = count_res.scalar() or 0

    participants_statement = (
        select(User)
        .join(UserChallenge, User.id == UserChallenge.user_id)
        .where(UserChallenge.challenge_id == challenge.id)
        .order_by(desc(UserChallenge.joined_at))
        .limit(5)
    )

    participants_res = await session.execute(participants_statement)
    top_participants = participants_res.scalars().all()

    base_data = ChallengeSchema.model_validate(challenge).model_dump()
    return ChallengeWithParticipantsSummarySchema(
        **base_data,
        participants_count=total_participants,
        preview_participants=[
            ParticipantPreviewSchema.model_validate(u) for u in top_participants
        ],
    )


async def set_challenge_winners(
    session: AsyncSession,
    challenge_id: int,
    winner_user_ids: list[str],
    super_winner_user_ids: list[str],
) -> ChallengeWithDetailsSchema:
    logger.info(f"Setting winner for challenge { challenge_id }")

    statement = (
        select(Challenge)
        .where(Challenge.id == challenge_id)
        .options(
            selectinload(Challenge.winners),
            selectinload(Challenge.super_winners),
            selectinload(Challenge.challenge_books)
            .selectinload(ChallengeBook.book)
            .options(selectinload(Book.genres), selectinload(Book.authors)),
            selectinload(Challenge.participants).selectinload(UserChallenge.user),
        )
    )

    result = await session.execute(statement)
    challenge = result.scalar_one_or_none()

    if not challenge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Challenge not found"
        )

    winners_res = await session.execute(
        select(User).where(User.id.in_(winner_user_ids))
    )

    super_winners_res = await session.execute(
        select(User).where(User.id.in_(super_winner_user_ids))
    )

    challenge.winners = list(winners_res.scalars().all())
    challenge.super_winners = list(super_winners_res.scalars().all())

    challenge.active = False

    await session.commit()
    await session.refresh(challenge)

    return ChallengeWithDetailsSchema.model_validate(challenge)
