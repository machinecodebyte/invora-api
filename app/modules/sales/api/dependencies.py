from fastapi import Depends

from app.db.session import get_db_session
from app.modules.sales.application.service import SalesUploadService
from app.modules.sales.infrastructure.repositories import SalesUploadRepository


async def get_sales_upload_service(
    session=Depends(get_db_session),
) -> SalesUploadService:
    return SalesUploadService(repository=SalesUploadRepository(session))
