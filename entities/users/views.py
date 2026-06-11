from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Response,
    Request,
    BackgroundTasks,
    status,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import db_helper
from core.redis_config import redis_client
from entities.users.schema import SignupRequest, VerifyOTPRequest
from . import service, crud

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register")
async def register(
    data: SignupRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    try:
        user, otp = await service.register_user(data, session, redis_client)
        background_tasks.add_task(
            service.send_otp_email, str(user.email), user.username, otp
        )
        return {"message": "OTP send", "email": user.email}
    except IntegrityError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=e.__notes__[0])


@router.post("/send-otp")
async def send_otp(
    user_email: str,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    user = await crud.get_user_by_email(session, user_email)
    new_otp = service.generate_random_otp()
    await redis_client.set(f"otp:{user_email}", new_otp, ex=300)
    try:
        background_tasks.add_task(
            service.send_otp_email, str(user_email), user.username, new_otp
        )
        return {"message": "New OTP send", "email": user.email}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/verify")
async def verify(
    data: VerifyOTPRequest,
    response: Response,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    try:
        user = await service.verify_otp(
            str(data.email), data.otp, session, redis_client
        )

        access_token, refresh_token = service.generate_auth_tokens(user.id)

        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            max_age=15 * 60,
            samesite="lax",
            secure=False,
        )

        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            max_age=7 * 24 * 60 * 60,
            samesite="lax",
            secure=False,
        )

        return {"message": "verified"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/logout")
async def logout(request: Request, response: Response):
    access_token = request.cookies.get("access_token")
    refresh_token = request.cookies.get("refresh_token")

    if access_token:
        await service.add_token_to_blacklist(access_token, redis_client)
    if refresh_token:
        await service.add_token_to_blacklist(refresh_token, redis_client)

    response.delete_cookie(
        key="access_token", httponly=True, samesite="lax", secure=False
    )

    response.delete_cookie(
        key="refresh_token", httponly=True, samesite="lax", secure=False
    )

    return {"message": "Logout successful"}
