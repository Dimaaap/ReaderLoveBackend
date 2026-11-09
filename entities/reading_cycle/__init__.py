from fastapi import APIRouter

from .views import router as reading_cycle_router

router = APIRouter()
router.include_router(reading_cycle_router, prefix="/reading_cycles")
