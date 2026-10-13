from fastapi import APIRouter

from .views import router as statistics_router

router = APIRouter()
router.include_router(statistics_router, prefix="/statistics")
