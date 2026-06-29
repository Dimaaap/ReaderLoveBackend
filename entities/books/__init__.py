from fastapi import APIRouter

from .views import router as books_router

router = APIRouter()
router.include_router(books_router, prefix="/books")
