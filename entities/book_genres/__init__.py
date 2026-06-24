from fastapi import APIRouter

from .views import router as book_genres_router

router = APIRouter()
router.include_router(book_genres_router, prefix="/book_genres")
