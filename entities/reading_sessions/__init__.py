from fastapi import APIRouter

from .views import router as reading_session_router

router = APIRouter()
router.include_router(reading_session_router, prefix="/reading-sessions")
