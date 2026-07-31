import os
import httpx

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Response,
    Request,
    BackgroundTasks,
    status,
    Query,
    UploadFile,
    File,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import db_helper
from core.redis_config import redis_client
from entities.users.schema import (
    SignupRequest,
    VerifyOTPRequest,
    LoginSchema,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    UpdateUserPartial,
    ChangePasswordSchema,
    UpdateUserSettings,
    UserByUsernameSchema,
)
from . import service, crud
from .exceptions import GitHubException
from ..user_settings.schema import UserSettingsSchema

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


@router.post("/forgot-password")
async def forgot_password(
    data: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    user_email = str(data.email)
    user = await crud.get_user_by_email(session, user_email)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    reset_otp = service.generate_random_otp()
    await redis_client.set(f"reset_otp:{user_email}", reset_otp, ex=300)

    try:
        background_tasks.add_task(
            service.send_reset_password_email, user_email, user.username, reset_otp
        )
        return {"message": "Reset OTP send successfully", "email": user_email}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/user/{username}")
async def get_user_by_username(
    username: str, session: AsyncSession = Depends(db_helper.scoped_session_dependency)
):
    user = await crud.get_user_by_username(session, username)

    return user


@router.post("/reset-password")
async def reset_password(
    data: ResetPasswordRequest,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    saved_otp = await redis_client.get(f"reset_otp:{data.email}")
    if not saved_otp or saved_otp != data.otp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired code"
        )
    try:
        await service.update_user_password(session, str(data.email), data.new_password)
        await redis_client.delete(f"reset_otp:{data.email}")

        return {"message": "Password updated successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update password",
        )


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

        service.set_auth_cookies(response, access_token, refresh_token)

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

    service.delete_auth_cookies(response)

    return {"message": "Logout successful"}


@router.post("/login")
async def login(
    data: LoginSchema,
    response: Response,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    user = await service.authenticate_user(data, session)

    access_token, refresh_token = service.generate_auth_tokens(user.id)
    service.set_auth_cookies(response, access_token, refresh_token)

    return {
        "message": "Login successful",
        "user": {"id": user.id, "email": user.email, "username": user.username},
    }


@router.get("/me")
async def get_current_user(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):

    access_token = request.cookies.get("access_token")
    refresh_token = request.cookies.get("refresh_token")

    user_id = None

    if access_token:
        is_blacklisted = await service.is_token_blacklisted(access_token, redis_client)
        if not is_blacklisted:
            user_id = service.try_get_user_id_from_token(
                access_token, expected_type="access"
            )

    if not user_id:
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
            )

        is_refresh_blacklisted = await service.is_token_blacklisted(
            refresh_token, redis_client
        )
        if is_refresh_blacklisted:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Session revoked"
            )

        try:
            user_id = await service.refresh_tokens(refresh_token, response)
        except HTTPException:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expired",
            )

    user = await crud.get_user_by_id(session, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )

    return {
        "avatar": user.avatar,
        "about_info": user.about_info,
        "username": user.username,
        "email": user.email,
        "avatar_color": user.avatar_color,
        "role": user.role,
        "register_way": user.register_way,
        "settings": UserSettingsSchema.model_validate(user.settings),
    }


@router.delete("/me/avatar")
async def delete_avatar(
    request: Request,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    access_token = request.cookies.get("access_token")

    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Not authenticated"
        )

    if await service.is_token_blacklisted(access_token, redis_client):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Session revoked"
        )

    user_id = service.get_user_id_from_token(access_token, expected_type="access")
    user = await crud.get_user_by_id(session, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    await service.delete_avatar(user.avatar)
    await crud.delete_avatar(session, user)

    return {"message": "Avatar deleted"}


@router.patch("/me/change-password")
async def change_password(
    data: ChangePasswordSchema,
    request: Request,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    access_token = request.cookies.get("access_token")

    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    if await service.is_token_blacklisted(access_token, redis_client):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired",
        )

    user_id = service.try_get_user_id_from_token(
        access_token,
        expected_type="access",
    )

    user = await crud.get_user_by_id(session, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    user = await service.change_password(
        session,
        user,
        data.current_password,
        data.new_password,
    )

    return {"message": "Success"}


@router.patch("/me/settings", response_model=UserSettingsSchema)
async def update_user_settings(
    settings_update: UpdateUserSettings,
    request: Request,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    access_token = request.cookies.get("access_token")

    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    if await service.is_token_blacklisted(access_token, redis_client):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired",
        )

    user_id = service.try_get_user_id_from_token(
        access_token,
        expected_type="access",
    )

    user = await crud.get_user_by_id(session, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return await crud.update_user_settings(session, user, settings_update)


@router.patch("/me")
async def patch_user_data(
    request: Request,
    data: UpdateUserPartial,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    access_token = request.cookies.get("access_token")

    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    if await service.is_token_blacklisted(access_token, redis_client):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired"
        )

    user_id = service.try_get_user_id_from_token(access_token, expected_type="access")

    user = await crud.get_user_by_id(session, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Not found user"
        )

    updated_user = await crud.update_user(session, user, data, partial=True)
    return updated_user


@router.patch("/me/avatar")
async def upload_avatar(
    request: Request,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    access_token = request.cookies.get("access_token")

    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    if await service.is_token_blacklisted(access_token, redis_client):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired"
        )

    user_id = service.try_get_user_id_from_token(access_token, expected_type="access")

    user = await crud.get_user_by_id(session, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Not found user"
        )

    avatar_path = await service.save_avatar(file, user.avatar)

    user = await crud.update_avatar(session, user, avatar_path)

    avatar = None

    if user.avatar:
        avatar = f"http://localhost:8030{user.avatar}"

    return {
        "avatar": avatar,
        "about_info": user.about_info,
        "username": user.username,
        "email": user.email,
        "avatar_color": user.avatar_color,
        "role": user.role,
        "register_way": user.register_way,
    }


@router.get("/google/callback")
async def google_callback(
    code: str = Query(None),
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Code not provided by Google",
        )

    token_url = os.getenv("GOOGLE_TOKEN_URI")
    data = {
        "code": code,
        "client_id": os.getenv("GOOGLE_CLIENT_ID"),
        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
        "redirect_uri": os.getenv("GOOGLE_REDIRECT_URI"),
        "grant_type": "authorization_code",
    }

    async with httpx.AsyncClient() as client:
        return await service.google_response(client, token_url, data, session)


@router.get("/github/callback")
async def github_callback(
    code: str = Query(None),
    error: str = Query(None),
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    if error:
        raise GitHubException(
            detail=f"Github error: {error}", status_code=status.HTTP_400_BAD_REQUEST
        )

    if not code:
        raise GitHubException(
            detail="Code is not provided by GitHub",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    token_url = os.getenv("GITHUB_TOKEN_URL")
    data = {
        "client_id": os.getenv("GITHUB_CLIENT_ID"),
        "client_secret": os.getenv("GITHUB_CLIENT_SECRET"),
        "code": code,
        "redirect_uri": os.getenv("GITHUB_REDIRECT_URI"),
    }

    headers = {"Accept": "application/json"}

    async with httpx.AsyncClient() as client:
        return await service.github_response(client, token_url, data, headers, session)
