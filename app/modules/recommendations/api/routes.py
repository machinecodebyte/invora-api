from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.modules.auth.api.dependencies import get_current_user
from app.modules.recommendations.api.dependencies import (
    get_reorder_recommendation_service,
)
from app.modules.recommendations.api.schemas import (
    GenerateRecommendationsData,
    GenerateRecommendationsRequest,
    GenerateRecommendationsResponse,
    RecommendationStatusUpdateRequest,
    RecommendationStatusUpdateResponse,
    RecommendationSummaryData,
    RecommendationSummaryResponse,
    ReorderRecommendationData,
    ReorderRecommendationListData,
    ReorderRecommendationListResponse,
    ReorderRecommendationPublic,
    ReorderRecommendationResponse,
    RunRecommendationListData,
    RunRecommendationListResponse,
)
from app.modules.recommendations.application.service import (
    ReorderRecommendationService,
)

router = APIRouter(prefix="/recommendations", tags=["Reorder Recommendations"])


@router.post(
    "/runs/{run_id}/generate",
    response_model=GenerateRecommendationsResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate reorder recommendations",
    description=(
        "Requires a Bearer access token and creates one recommendation per "
        "forecasted product for an owned completed forecast run. Existing "
        "recommendations return 409 unless refresh is true; refresh replaces "
        "only recommendations for that run."
    ),
)
async def generate_recommendations(
    run_id: UUID,
    payload: GenerateRecommendationsRequest,
    current_user: Annotated[object, Depends(get_current_user)],
    recommendation_service: Annotated[
        ReorderRecommendationService,
        Depends(get_reorder_recommendation_service),
    ],
) -> GenerateRecommendationsResponse:
    result = await recommendation_service.generate_for_forecast_run(
        user_id=current_user.id,
        run_id=run_id,
        refresh=payload.refresh,
    )
    return GenerateRecommendationsResponse(data=GenerateRecommendationsData(**result))


@router.get(
    "",
    response_model=ReorderRecommendationListResponse,
    status_code=status.HTTP_200_OK,
    summary="List reorder recommendations",
    description=(
        "Requires a Bearer access token and returns paginated recommendation "
        "rows owned by the current user. This endpoint reads recommendation "
        "decisions only and does not mutate inventory."
    ),
)
async def list_recommendations(
    current_user: Annotated[object, Depends(get_current_user)],
    recommendation_service: Annotated[
        ReorderRecommendationService,
        Depends(get_reorder_recommendation_service),
    ],
    forecast_run_id: UUID | None = Query(default=None),
    product_id: UUID | None = Query(default=None),
    category_id: UUID | None = Query(default=None),
    risk_level: str | None = Query(default=None),
    recommendation_status: str | None = Query(default=None, alias="status"),
    action: str | None = Query(default=None),
    generated_from: datetime | None = Query(default=None),
    generated_to: datetime | None = Query(default=None),
    search: str | None = Query(default=None, max_length=255),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    sort_by: str = Query(default="generated_at"),
    sort_order: str = Query(default="desc"),
) -> ReorderRecommendationListResponse:
    result = await recommendation_service.list_recommendations(
        user_id=current_user.id,
        forecast_run_id=forecast_run_id,
        product_id=product_id,
        category_id=category_id,
        risk_level=risk_level,
        status=recommendation_status,
        action=action,
        generated_from=generated_from,
        generated_to=generated_to,
        search=search,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return ReorderRecommendationListResponse(
        data=ReorderRecommendationListData(**result),
    )


@router.get(
    "/runs/{run_id}",
    response_model=RunRecommendationListResponse,
    status_code=status.HTTP_200_OK,
    summary="List recommendations for a forecast run",
    description=(
        "Requires a Bearer access token and returns generated recommendations "
        "for an owned forecast run."
    ),
)
async def list_run_recommendations(
    run_id: UUID,
    current_user: Annotated[object, Depends(get_current_user)],
    recommendation_service: Annotated[
        ReorderRecommendationService,
        Depends(get_reorder_recommendation_service),
    ],
    product_id: UUID | None = Query(default=None),
    risk_level: str | None = Query(default=None),
    recommendation_status: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    sort_by: str = Query(default="risk_level"),
    sort_order: str = Query(default="desc"),
) -> RunRecommendationListResponse:
    result = await recommendation_service.list_for_forecast_run(
        user_id=current_user.id,
        run_id=run_id,
        product_id=product_id,
        risk_level=risk_level,
        status=recommendation_status,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return RunRecommendationListResponse(data=RunRecommendationListData(**result))


@router.get(
    "/runs/{run_id}/summary",
    response_model=RecommendationSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get recommendation summary",
    description=(
        "Requires a Bearer access token and returns risk counts, total reorder "
        "quantity, and top reorder products for an owned forecast run."
    ),
)
async def get_recommendation_summary(
    run_id: UUID,
    current_user: Annotated[object, Depends(get_current_user)],
    recommendation_service: Annotated[
        ReorderRecommendationService,
        Depends(get_reorder_recommendation_service),
    ],
) -> RecommendationSummaryResponse:
    result = await recommendation_service.get_summary_for_forecast_run(
        user_id=current_user.id,
        run_id=run_id,
    )
    return RecommendationSummaryResponse(data=RecommendationSummaryData(**result))


@router.get(
    "/{recommendation_id}",
    response_model=ReorderRecommendationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get recommendation detail",
    description="Requires a Bearer access token and returns an owned recommendation.",
)
async def get_recommendation(
    recommendation_id: UUID,
    current_user: Annotated[object, Depends(get_current_user)],
    recommendation_service: Annotated[
        ReorderRecommendationService,
        Depends(get_reorder_recommendation_service),
    ],
) -> ReorderRecommendationResponse:
    recommendation = await recommendation_service.get_recommendation(
        user_id=current_user.id,
        recommendation_id=recommendation_id,
    )
    return ReorderRecommendationResponse(
        data=ReorderRecommendationData(
            recommendation=ReorderRecommendationPublic(**recommendation),
        )
    )


@router.patch(
    "/{recommendation_id}/status",
    response_model=RecommendationStatusUpdateResponse,
    status_code=status.HTTP_200_OK,
    summary="Update recommendation status",
    description=(
        "Requires a Bearer access token and marks an owned recommendation as "
        "acknowledged or dismissed. This does not create purchase orders or "
        "change inventory stock."
    ),
)
async def update_recommendation_status(
    recommendation_id: UUID,
    payload: RecommendationStatusUpdateRequest,
    current_user: Annotated[object, Depends(get_current_user)],
    recommendation_service: Annotated[
        ReorderRecommendationService,
        Depends(get_reorder_recommendation_service),
    ],
) -> RecommendationStatusUpdateResponse:
    recommendation = await recommendation_service.update_status(
        user_id=current_user.id,
        recommendation_id=recommendation_id,
        status=payload.status,
    )
    return RecommendationStatusUpdateResponse(
        data=ReorderRecommendationData(
            recommendation=ReorderRecommendationPublic(**recommendation),
        )
    )
