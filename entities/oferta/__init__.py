from fastapi import APIRouter

from .views import router as oferta_router

router = APIRouter()
router.include_router(oferta_router, prefix="/oferta")
