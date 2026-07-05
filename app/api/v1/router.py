from fastapi import APIRouter

from app.api.v1 import health
from app.modules.auth.api.routes import router as auth_router
from app.modules.users.api.routes import router as users_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(health.router, tags=["health"])
