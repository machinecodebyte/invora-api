from fastapi import Depends

from app.db.session import get_db_session
from app.modules.users.application.service import UserProfileService
from app.modules.users.infrastructure.repositories import UserProfileRepository


async def get_user_profile_service(
    session=Depends(get_db_session),
) -> UserProfileService:
    return UserProfileService(repository=UserProfileRepository(session))
