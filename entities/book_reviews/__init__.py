from fastapi import APIRouter

from .views import router as book_reviews_router

router = APIRouter()
router.include_router(book_reviews_router, prefix="/book-reviews")
