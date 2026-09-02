import json

from loguru import logger
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from core.redis_config import redis_client
from core.models import db_helper
from entities.book_reviews.schema import (
    BookReviewCreate,
    BookReviewSchema,
    BookReviewUpdatePartial,
)

from core.models import Book

from . import crud
from .tasks import check_review_for_spoiler_tasks

router = APIRouter(tags=["Book Router"])


@router.get("/", response_model=list[BookReviewSchema])
async def get_all_book_reviews(
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    cache_key = "book_reviews:all"
    cached = await redis_client.get(cache_key)

    if cached:
        logger.info("Get all book reviews from Redis cache")
        return json.loads(cached)

    data = await crud.get_all_book_reviews(session)
    serialized_data = json.dumps([item.model_dump(mode="json") for item in data])
    logger.info("Return all book reviews from db")

    await redis_client.set(cache_key, serialized_data, ex=300)
    return data


@router.post("/", response_model=BookReviewSchema, status_code=201)
async def create_book_review(
    data: BookReviewCreate,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    book_review = await crud.create_book_review(session, data)
    await redis_client.delete(f"book_reviews:all")
    review_keys = [
        key
        async for key in redis_client.scan_iter(f"book_reviews:book:{data.book_id}:*")
    ]
    if review_keys:
        await redis_client.delete(*review_keys)
    book = await session.get(Book, data.book_id)
    if book:
        await redis_client.delete(f"books:{book.slug}")

        if book_review.text:
            background_tasks.add_task(
                check_review_for_spoiler_tasks,
                review_id=book_review.id,
                book_title=book.title,
                review_text=book_review.text,
            )
    return book_review


@router.get("/by-username", response_model=list[BookReviewSchema])
async def get_book_review_by_username(
    username: str, session: AsyncSession = Depends(db_helper.scoped_session_dependency)
):
    data = await crud.get_user_reviews(username, session)
    return data


@router.get("/by-book-id", response_model=list[BookReviewSchema])
async def get_book_reviews(
    book_id: int,
    limit: int = 5,
    offset: int = 0,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    cache_key = f"book_reviews:book:{book_id}:limit:{limit}:offset:{offset}"
    cached = await redis_client.get(cache_key)

    if cached:
        logger.info(
            f"Get all reviews for book with id {book_id} query params: limit={limit}, "
            f"offset={offset} from Redis cache"
        )
        return json.loads(cached)

    data = await crud.get_book_reviews(book_id, session, limit, offset)
    serialized_data = json.dumps([item.model_dump(mode="json") for item in data])
    logger.info(
        f"Return all review for book with id {book_id} query params: limit={limit}, offset={offset} from db"
    )
    await redis_client.set(cache_key, serialized_data, ex=300)
    return data


@router.get("/{review_id}", response_model=BookReviewSchema)
async def get_book_review_by_id(
    review_id: int, session: AsyncSession = Depends(db_helper.scoped_session_dependency)
):
    cache_key = f"book_reviews:{review_id}"
    cached = await redis_client.get(cache_key)

    if cached:
        logger.info(f"Get book review with id {review_id}")
        return json.loads(cached)

    db_review = await crud.get_book_review_by_id(session, review_id)

    if not db_review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Book review not found"
        )

    logger.info(f"Return book review with id {review_id} from db")
    await redis_client.set(cache_key, db_review.model_dump_json(), ex=300)
    return db_review


@router.patch("/{review_id}", response_model=BookReviewSchema)
async def update_book_review(
    review_id: int,
    data: BookReviewUpdatePartial,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    existing_review = await crud.get_book_review_by_id(session, review_id)

    if not existing_review:
        logger.error(f"Failed to update book review. Review {review_id} was not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Book review not found"
        )

    updated_review = await crud.update_book_review(
        session, review_id, data, partial=True
    )

    try:
        await redis_client.delete("book_reviews:all")
        await redis_client.delete(f"book_reviews:{review_id}")
        await redis_client.delete(f"book_reviews:book:{existing_review.book_id}")
    except Exception:
        pass

    return updated_review


@router.delete("/{review_id}")
async def delete_book_review_by_id(
    review_id: int, session: AsyncSession = Depends(db_helper.scoped_session_dependency)
):
    is_deleted, deleted_review = await crud.delete_book_review(session, review_id)

    if is_deleted:
        try:
            await redis_client.delete("book_reviews:all")
            await redis_client.delete(f"book_reviews:{review_id}")

            if deleted_review.user:
                await redis_client.delete(f"book_reviews:book:{deleted_review.book_id}")
        except Exception:
            pass
