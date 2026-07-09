from fastapi import APIRouter

from app.api.v1 import health
from app.modules.auth.api.routes import router as auth_router
from app.modules.forecasting.api.ml_routes import router as ml_forecasting_router
from app.modules.forecasting.api.result_routes import router as forecast_results_router
from app.modules.forecasting.api.routes import router as forecasting_router
from app.modules.inventory.api.routes import router as inventory_router
from app.modules.products.api.routes import router as products_router
from app.modules.recommendations.api.routes import router as recommendations_router
from app.modules.sales.api.routes import router as sales_router
from app.modules.users.api.routes import router as users_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(products_router)
api_router.include_router(inventory_router)
api_router.include_router(sales_router)
api_router.include_router(forecasting_router)
api_router.include_router(ml_forecasting_router)
api_router.include_router(forecast_results_router)
api_router.include_router(recommendations_router)
api_router.include_router(health.router, tags=["health"])
