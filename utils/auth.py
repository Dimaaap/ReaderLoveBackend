from fastapi import Depends, HTTPException, Request, status

from core.redis_config import redis_client
from entities.users import service as auth_service


async def get_current_user_id(request: Request) -> str:
    access_token = request.cookies.get("access_token")

    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    if await auth_service.is_token_blacklisted(access_token, redis_client):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired",
        )

    user_id = auth_service.try_get_user_id_from_token(
        access_token, expected_type="access"
    )
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    return user_id
