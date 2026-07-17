"""Top-level API router composition."""

from fastapi import APIRouter

from kalibr_publisher.api.routes.health import router as health_router
from kalibr_publisher.api.routes.posts import router as posts_router
from kalibr_publisher.api.routes.telegram import router as telegram_router
from kalibr_publisher.api.routes.users import router as users_router
from kalibr_publisher.api.routes.content_plan import router as content_plan_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(posts_router)
api_router.include_router(telegram_router)
api_router.include_router(users_router)
api_router.include_router(content_plan_router)
