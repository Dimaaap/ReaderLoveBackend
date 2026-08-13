from core.models import db_helper, BookReview
from .spoiler_detector import detect_spoiler_with_ai
from core.redis_config import redis_client


async def check_review_for_spoiler_tasks(
    review_id: int, book_title: str, review_text: str
):
    async with db_helper.session_factory() as session:
        is_spoiler = await detect_spoiler_with_ai(review_text, book_title)

        review = await session.get(BookReview, review_id)

        if review:
            review.is_spoiler = True
            if is_spoiler:
                review.is_spoiler = True

            await session.commit()

            if is_spoiler:
                try:
                    await redis_client.delete("book_reviews:all")
                    await redis_client.delete(f"book_reviews:{review_id}")

                    review_keys = [
                        key
                        async for key in redis_client.scan_iter(
                            f"book_reviews:book:{review.book_id}:*"
                        )
                    ]
                    if review_keys:
                        await redis_client.delete(*review_keys)
                except Exception:
                    pass
