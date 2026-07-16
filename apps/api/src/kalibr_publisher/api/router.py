"""Top-level API router composition."""

from fastapi import APIRouter

from kalibr_publisher.api.routes.health import router as health_router
from kalibr_publisher.api.routes.telegram import router as telegram_router
from kalibr_publisher.api.routes.posts import router as posts_router
from kalibr_publisher.api.routes.automation import router as automation_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(telegram_router)
api_router.include_router(posts_router)
api_router.include_router(automation_router)
