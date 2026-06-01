from fastapi import APIRouter

from .views import router as social_links_router

router = APIRouter()
router.include_router(social_links_router, prefix="/social_links")
