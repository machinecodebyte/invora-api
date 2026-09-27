"""Central SQLAlchemy model registry.

Every process that opens an application database session (HTTP server, Alembic,
or an RQ worker) must register the same mapped tables before SQLAlchemy resolves
foreign-key dependencies. Importing this module is that explicit boundary.
"""

from app.modules.auth.infrastructure.models import RefreshTokenModel, UserModel
from app.modules.forecasting.infrastructure.models import (
    ForecastModelMetricModel,
    ForecastPredictionModel,
    ForecastRunModel,
)
from app.modules.inventory.infrastructure.models import (
    InventoryItemModel,
    InventoryStockMovementModel,
)
from app.modules.jobs.infrastructure.models import BackgroundJobModel
from app.modules.products.infrastructure.models import (
    ProductCategoryModel,
    ProductModel,
)
from app.modules.recommendations.infrastructure.models import ReorderRecommendationModel
from app.modules.sales.infrastructure.models import (
    SalesTransactionModel,
    SalesUploadBatchModel,
    SalesUploadRejectedRowModel,
)
from app.modules.settings.infrastructure.models import UserSystemSettingsModel

__all__ = [
    "BackgroundJobModel",
    "ForecastModelMetricModel",
    "ForecastPredictionModel",
    "ForecastRunModel",
    "InventoryItemModel",
    "InventoryStockMovementModel",
    "ProductCategoryModel",
    "ProductModel",
    "RefreshTokenModel",
    "ReorderRecommendationModel",
    "SalesTransactionModel",
    "SalesUploadBatchModel",
    "SalesUploadRejectedRowModel",
    "UserModel",
    "UserSystemSettingsModel",
    "ensure_models_registered",
]


def ensure_models_registered() -> None:
    """Make the registry import explicit at application process boundaries."""
