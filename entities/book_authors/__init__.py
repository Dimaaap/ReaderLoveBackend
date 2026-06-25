from fastapi import APIRouter

from .views import router as book_authors_router

router = APIRouter()
router.include_router(book_authors_router, prefix="/book_authors")
