from fastapi import APIRouter

from .views import router as books_selection_router

router = APIRouter()
router.include_router(books_selection_router, prefix="/books_selections")
