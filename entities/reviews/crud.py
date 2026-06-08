from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from entities.reviews.schema import (
    ReviewSchema,
    ReviewCreate,
    ReviewUpdate,
    ReviewUpdatePartial,
)

from core.models import Review


async def get_all_reviews(session: AsyncSession) -> list[ReviewSchema]:
    statement = select(Review)

    result = await session.execute(statement)
    reviews = result.scalars().all()

    return [ReviewSchema.model_validate(review) for review in reviews]


async def create_review(session: AsyncSession, data: ReviewCreate) -> ReviewSchema:
    new_review = Review(**data.model_dump())

    session.add(new_review)
    await session.commit()
    await session.refresh(new_review)

    return ReviewSchema.model_validate(new_review)


async def get_review_by_id(session: AsyncSession, id: int) -> Review | None:
    statement = select(Review).where(Review.id == id)

    result = await session.execute(statement)
    review = result.scalar_one_or_none()

    if review is None:
        return None

    return review


async def update_review(
    session: AsyncSession, id: int, data: ReviewUpdate
) -> ReviewSchema | None:
    statement = select(Review).where(Review.id == id)

    result = await session.execute(statement)
    review = result.scalar_one_or_none()

    if review is None:
        return None

    for key, value in data.model_dump().items():
        setattr(review, key, value)

    await session.commit()
    await session.refresh(review)

    return ReviewSchema.model_validate(review)


async def partial_update_review(
    session: AsyncSession, id: int, data: ReviewUpdatePartial
):
    statement = select(Review).where(Review.id == id)
    result = await session.execute(statement)
    review = result.scalar_one_or_none()

    if review is None:
        return None

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(review, key, value)

    await session.commit()
    await session.refresh(review)

    return ReviewSchema.model_validate(review)


async def delete_review(session: AsyncSession, id: int) -> bool:
    result = await session.execute(select(Review).where(Review.id == id))

    review = result.scalar_one_or_none()

    if review is None:
        return False

    await session.delete(review)
    await session.commit()
    return True
