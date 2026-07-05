from fastapi import Depends

from app.db.session import get_db_session
from app.modules.inventory.application.service import InventoryService
from app.modules.inventory.infrastructure.repositories import InventoryRepository


async def get_inventory_service(session=Depends(get_db_session)) -> InventoryService:
    return InventoryService(repository=InventoryRepository(session))
