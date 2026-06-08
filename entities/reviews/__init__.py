from fastapi import APIRouter

from .views import router as reviews_router

router = APIRouter()
router.include_router(reviews_router, prefix="/reviews")
