from fastapi import APIRouter

from .views import router as book_publisher_router

router = APIRouter()
router.include_router(book_publisher_router, prefix="/book_publishers")
