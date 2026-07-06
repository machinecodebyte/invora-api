from fastapi import Depends

from app.db.session import get_db_session
from app.modules.sales.application.service import (
    SalesTransactionService,
    SalesUploadService,
)
from app.modules.sales.infrastructure.repositories import (
    SalesTransactionRepository,
    SalesUploadRepository,
)


async def get_sales_upload_service(
    session=Depends(get_db_session),
) -> SalesUploadService:
    return SalesUploadService(repository=SalesUploadRepository(session))


async def get_sales_transaction_service(
    session=Depends(get_db_session),
) -> SalesTransactionService:
    return SalesTransactionService(repository=SalesTransactionRepository(session))
