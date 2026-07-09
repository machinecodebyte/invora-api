from fastapi import Depends

from app.db.session import get_db_session
from app.modules.recommendations.application.service import (
    ReorderRecommendationService,
)
from app.modules.recommendations.infrastructure.repositories import (
    ReorderRecommendationRepository,
)


async def get_reorder_recommendation_service(
    session=Depends(get_db_session),
) -> ReorderRecommendationService:
    return ReorderRecommendationService(
        repository=ReorderRecommendationRepository(session),
    )
