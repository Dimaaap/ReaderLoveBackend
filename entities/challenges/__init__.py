from fastapi import APIRouter

from .views import router as challenges_router

router = APIRouter()
router.include_router(challenges_router, prefix="/challenges")
