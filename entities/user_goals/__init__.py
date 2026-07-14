from fastapi import APIRouter

from .views import router as user_goals_router

router = APIRouter()
router.include_router(user_goals_router, prefix="/user-goals")
