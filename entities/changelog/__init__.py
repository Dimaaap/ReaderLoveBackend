from fastapi import APIRouter

from .views import router as changelog_router

router = APIRouter()
router.include_router(changelog_router, prefix="/changelog")
