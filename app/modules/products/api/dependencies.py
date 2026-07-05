from fastapi import Depends

from app.db.session import get_db_session
from app.modules.products.application.service import ProductService
from app.modules.products.infrastructure.repositories import ProductRepository


async def get_product_service(session=Depends(get_db_session)) -> ProductService:
    return ProductService(repository=ProductRepository(session))
