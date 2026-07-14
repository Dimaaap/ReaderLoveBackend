from fastapi import APIRouter

from .social_links import router as social_links_router
from .reviews import router as reviews_router
from .oferta import router as oferta_router
from .users import router as users_router
from .book_genres import router as book_genres_router
from .book_authors import router as book_authors_router
from .books import router as books_router
from .template_quotes import router as template_quotes_router
from .reading_sessions import router as reading_sessions_router
from .book_notes import router as book_notes_router
from .user_goals import router as user_goal_router
from .user_goals_progress import router as user_goals_progress_router

router = APIRouter(prefix="/api/v1")
router.include_router(social_links_router)
router.include_router(reviews_router)
router.include_router(oferta_router)
router.include_router(users_router)
router.include_router(book_genres_router)
router.include_router(book_authors_router)
router.include_router(books_router)
router.include_router(template_quotes_router)
router.include_router(reading_sessions_router)
router.include_router(book_notes_router)
router.include_router(user_goal_router)
router.include_router(user_goals_progress_router)
