from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.modules.auth.api.dependencies import get_current_user
from app.modules.dashboard.api.dependencies import get_dashboard_analytics_service
from app.modules.dashboard.api.schemas import (
    DashboardDemandTrendData,
    DashboardDemandTrendResponse,
    DashboardForecastOverviewData,
    DashboardForecastOverviewResponse,
    DashboardInventoryRiskData,
    DashboardInventoryRiskResponse,
    DashboardKpiData,
    DashboardKpiResponse,
    DashboardRecentActivityData,
    DashboardRecentActivityResponse,
    DashboardReorderAlertsData,
    DashboardReorderAlertsResponse,
    DashboardSummaryData,
    DashboardSummaryResponse,
)
from app.modules.dashboard.application.service import DashboardAnalyticsService

router = APIRouter(prefix="/dashboard", tags=["Dashboard Analytics"])


@router.get(
    "/summary",
    response_model=DashboardSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get dashboard summary",
    description=(
        "Requires a Bearer access token and returns a read-only dashboard "
        "overview combining KPIs, sales trends, inventory risk, forecast health, "
        "reorder alerts, and recent activity for the current user."
    ),
)
async def get_dashboard_summary(
    current_user: Annotated[object, Depends(get_current_user)],
    dashboard_service: Annotated[
        DashboardAnalyticsService,
        Depends(get_dashboard_analytics_service),
    ],
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    forecast_run_id: UUID | None = Query(default=None),
) -> DashboardSummaryResponse:
    result = await dashboard_service.get_summary(
        user_id=current_user.id,
        date_from=date_from,
        date_to=date_to,
        forecast_run_id=forecast_run_id,
    )
    return DashboardSummaryResponse(data=DashboardSummaryData(**result))


@router.get(
    "/kpis",
    response_model=DashboardKpiResponse,
    status_code=status.HTTP_200_OK,
    summary="Get dashboard KPIs",
    description=(
        "Requires a Bearer access token and returns user-scoped KPI counts from "
        "Products, Sales, Inventory, Forecasts, and Reorder Recommendations."
    ),
)
async def get_dashboard_kpis(
    current_user: Annotated[object, Depends(get_current_user)],
    dashboard_service: Annotated[
        DashboardAnalyticsService,
        Depends(get_dashboard_analytics_service),
    ],
) -> DashboardKpiResponse:
    result = await dashboard_service.get_kpis(user_id=current_user.id)
    return DashboardKpiResponse(data=DashboardKpiData(**result))


@router.get(
    "/demand-trends",
    response_model=DashboardDemandTrendResponse,
    status_code=status.HTTP_200_OK,
    summary="Get demand trend chart data",
    description=(
        "Requires a Bearer access token and returns chart-ready historical "
        "demand aggregates from non-deleted Sales Transactions."
    ),
)
async def get_dashboard_demand_trends(
    current_user: Annotated[object, Depends(get_current_user)],
    dashboard_service: Annotated[
        DashboardAnalyticsService,
        Depends(get_dashboard_analytics_service),
    ],
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    interval: str = Query(default="day"),
    product_id: UUID | None = Query(default=None),
    category_id: UUID | None = Query(default=None),
) -> DashboardDemandTrendResponse:
    result = await dashboard_service.get_demand_trends(
        user_id=current_user.id,
        date_from=date_from,
        date_to=date_to,
        interval=interval,
        product_id=product_id,
        category_id=category_id,
    )
    return DashboardDemandTrendResponse(data=DashboardDemandTrendData(**result))


@router.get(
    "/inventory-risk",
    response_model=DashboardInventoryRiskResponse,
    status_code=status.HTTP_200_OK,
    summary="Get inventory risk analytics",
    description=(
        "Requires a Bearer access token and returns inventory stock-status "
        "counts plus low-stock and out-of-stock previews."
    ),
)
async def get_dashboard_inventory_risk(
    current_user: Annotated[object, Depends(get_current_user)],
    dashboard_service: Annotated[
        DashboardAnalyticsService,
        Depends(get_dashboard_analytics_service),
    ],
    limit: int = Query(default=5, ge=1, le=50),
) -> DashboardInventoryRiskResponse:
    result = await dashboard_service.get_inventory_risk(
        user_id=current_user.id,
        limit=limit,
    )
    return DashboardInventoryRiskResponse(data=DashboardInventoryRiskData(**result))


@router.get(
    "/forecast-overview",
    response_model=DashboardForecastOverviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Get dashboard forecast overview",
    description=(
        "Requires a Bearer access token and returns latest forecast run health, "
        "status counts, latest metrics, and prediction summary. Empty forecast "
        "state returns a successful zero/null response."
    ),
)
async def get_dashboard_forecast_overview(
    current_user: Annotated[object, Depends(get_current_user)],
    dashboard_service: Annotated[
        DashboardAnalyticsService,
        Depends(get_dashboard_analytics_service),
    ],
) -> DashboardForecastOverviewResponse:
    result = await dashboard_service.get_forecast_overview(user_id=current_user.id)
    return DashboardForecastOverviewResponse(
        data=DashboardForecastOverviewData(**result),
    )


@router.get(
    "/reorder-alerts",
    response_model=DashboardReorderAlertsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get dashboard reorder alerts",
    description=(
        "Requires a Bearer access token and returns recommendation risk/status "
        "counts plus a top reorder preview. This endpoint does not generate "
        "new recommendations."
    ),
)
async def get_dashboard_reorder_alerts(
    current_user: Annotated[object, Depends(get_current_user)],
    dashboard_service: Annotated[
        DashboardAnalyticsService,
        Depends(get_dashboard_analytics_service),
    ],
    forecast_run_id: UUID | None = Query(default=None),
    risk_level: str | None = Query(default=None),
    recommendation_status: str | None = Query(default="open", alias="status"),
    limit: int = Query(default=10, ge=1, le=50),
) -> DashboardReorderAlertsResponse:
    result = await dashboard_service.get_reorder_alerts(
        user_id=current_user.id,
        forecast_run_id=forecast_run_id,
        risk_level=risk_level,
        status=recommendation_status,
        limit=limit,
    )
    return DashboardReorderAlertsResponse(data=DashboardReorderAlertsData(**result))


@router.get(
    "/recent-activity",
    response_model=DashboardRecentActivityResponse,
    status_code=status.HTTP_200_OK,
    summary="Get dashboard recent activity",
    description=(
        "Requires a Bearer access token and returns a read-only activity feed "
        "derived from sales uploads, forecast runs, stock movements, and "
        "generated recommendations."
    ),
)
async def get_dashboard_recent_activity(
    current_user: Annotated[object, Depends(get_current_user)],
    dashboard_service: Annotated[
        DashboardAnalyticsService,
        Depends(get_dashboard_analytics_service),
    ],
    limit: int = Query(default=10, ge=1, le=50),
) -> DashboardRecentActivityResponse:
    result = await dashboard_service.get_recent_activity(
        user_id=current_user.id,
        limit=limit,
    )
    return DashboardRecentActivityResponse(data=DashboardRecentActivityData(**result))
