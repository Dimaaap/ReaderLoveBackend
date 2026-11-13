from fastapi import APIRouter

from .views import router as countries_router

router = APIRouter()
router.include_router(countries_router, prefix="/countries")
