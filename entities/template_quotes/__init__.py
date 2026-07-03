from fastapi import APIRouter

from .views import router as template_quotes_router

router = APIRouter()
router.include_router(template_quotes_router, prefix="/template_quotes")
