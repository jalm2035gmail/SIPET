from fastapi import APIRouter

from .api import router as api_router
from .assets import router as assets_router
from .pages import router as pages_router
from .placeholders import router as placeholders_router


router = APIRouter()
router.include_router(api_router)
router.include_router(assets_router)
router.include_router(pages_router)
router.include_router(placeholders_router)

__all__ = ["router"]
