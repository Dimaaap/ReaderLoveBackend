from fastapi import APIRouter

from .social_links import router as social_links_router
from .reviews import router as reviews_router
from .oferta import router as oferta_router
from .users import router as users_router
from .book_genres import router as book_genres_router

router = APIRouter(prefix="/api/v1")
router.include_router(social_links_router)
router.include_router(reviews_router)
router.include_router(oferta_router)
router.include_router(users_router)
router.include_router(book_genres_router)
