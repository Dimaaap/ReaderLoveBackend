from fastapi import APIRouter

from .views import router as book_notes_router

router = APIRouter()
router.include_router(book_notes_router, prefix="/book-notes")
