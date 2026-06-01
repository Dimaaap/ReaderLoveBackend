from fastapi import APIRouter

from .social_links import router as social_links_router

router = APIRouter(prefix="/api/v1")
router.include_router(social_links_router)
