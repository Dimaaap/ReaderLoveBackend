from fastapi import APIRouter

from .views import router as book_collections_router

router = APIRouter()
router.include_router(book_collections_router, prefix="/book-collections")
