from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.db.session import check_database_ready
from app.shared.responses import error_response, success_response

router = APIRouter()


@router.get("/health", status_code=status.HTTP_200_OK)
async def health() -> dict[str, object]:
    return success_response({"status": "ok"})


@router.get("/health/ready", response_model=None)
async def readiness() -> dict[str, object] | JSONResponse:
    if await check_database_ready():
        return success_response({"status": "ready"})

    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=error_response(
            code="database_unavailable",
            message="Database is not ready.",
        ),
    )
