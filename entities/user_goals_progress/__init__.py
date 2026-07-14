from fastapi import APIRouter

from .views import router as user_goals_progress_router

router = APIRouter()
router.include_router(user_goals_progress_router, prefix="/user-goals-progress")
