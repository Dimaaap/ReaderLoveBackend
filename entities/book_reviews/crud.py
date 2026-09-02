from fastapi import HTTPException, status

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from core.models import BookReview, User
from entities.book_reviews.schema import (
    BookReviewCreate,
    BookReviewSchema,
    BookReviewUpdate,
    BookReviewUpdatePartial,
)


async def get_all_book_reviews(session: AsyncSession) -> list[BookReviewSchema]:
    logger.info("Try to get all book reviews")

    statement = (
        select(BookReview)
        .options(joinedload(BookReview.book), joinedload(BookReview.user))
        .order_by(BookReview.id)
    )

    result = await session.execute(statement)
    book_reviews = result.scalars().unique().all()
    return [BookReviewSchema.model_validate(review) for review in book_reviews]


async def get_user_reviews(
    username: str, session: AsyncSession, limit: int | None = None
) -> list[BookReviewSchema]:
    logger.info(f"Try to get all reviews for user {username} with limit {limit}")

    statement = (
        select(BookReview)
        .join(BookReview.user)
        .where(User.username == username)
        .options(joinedload(BookReview.book), joinedload(BookReview.user))
        .order_by(BookReview.created_at.desc())
    )

    if limit is not None:
        statement = statement.limit(limit)

    result = await session.execute(statement)
    book_reviews = result.scalars().unique().all()

    return [BookReviewSchema.model_validate(review) for review in book_reviews]


async def get_book_reviews(
    book_id: int, session: AsyncSession, limit: int = 5, offset: int = 0
) -> list[BookReviewSchema]:
    logger.info(
        f"Try to get all reviews for book {book_id} with query params:limit={limit}, offset={offset}"
    )

    statement = (
        select(BookReview)
        .where(BookReview.book_id == book_id)
        .options(joinedload(BookReview.book), joinedload(BookReview.user))
        .order_by(BookReview.created_at.desc())
        .limit(limit)
        .offset(offset)
    )

    result = await session.execute(statement)
    book_reviews = result.scalars().unique().all()

    return [BookReviewSchema.model_validate(review) for review in book_reviews]


async def get_book_review_by_id(
    session: AsyncSession, review_id: int
) -> BookReviewSchema | None:
    logger.info(f"Try to get book review with id {review_id}")
    statement = (
        select(BookReview)
        .where(BookReview.id == review_id)
        .options(joinedload(BookReview.book), joinedload(BookReview.user))
    )

    result = await session.execute(statement)
    review = result.scalar_one_or_none()

    if not review:
        logger.error(f"Failed to get book review with id {review_id}")
        return None

    return BookReviewSchema.model_validate(review)


async def create_book_review(
    session: AsyncSession, data: BookReviewCreate
) -> BookReviewSchema:
    logger.info(f"Try go create book review with data {data}")
    user_data = await session.execute(
        select(User).where(User.username == data.username)
    )
    user = user_data.scalar_one_or_none()
    if not user:
        logger.error("User was not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    book_review_data = data.model_dump(exclude={"user", "book", "username"})
    book_review = BookReview(**book_review_data, user_id=user.id)

    session.add(book_review)
    await session.commit()

    return await get_book_review_by_id(session, book_review.id)


async def update_book_review(
    session: AsyncSession,
    book_review_id: int,
    book_review_update: BookReviewUpdate | BookReviewUpdatePartial,
    partial: bool = False,
) -> BookReviewSchema:

    logger.info(
        f"Try to update book review with id {book_review_id} with data {book_review_update}"
    )
    result = await session.execute(
        select(BookReview).where(BookReview.id == book_review_id)
    )
    book_review = result.scalar_one_or_none()

    if not book_review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Book review not found"
        )

    update_data = book_review_update.model_dump(exclude_unset=partial)

    for key, value in update_data.items():
        setattr(book_review, key, value)

    await session.commit()

    return await get_book_review_by_id(session, book_review_id)


async def delete_book_review(
    session: AsyncSession, review_id: int
) -> tuple[bool, BookReviewSchema | None]:
    logger.info(f"Try to delete book review with id {review_id}")
    result = await session.execute(
        select(BookReview)
        .where(BookReview.id == review_id)
        .options(joinedload(BookReview.user), joinedload(BookReview.book))
    )

    book_review = result.scalar_one_or_none()

    if book_review is None:
        logger.error(
            f"Failed to delete book review with id {review_id} - book review was not found"
        )
        return False, None
    review_schema = BookReviewSchema.model_validate(book_review)

    await session.delete(book_review)
    await session.commit()

    return True, review_schema
