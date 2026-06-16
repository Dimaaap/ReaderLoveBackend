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
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import RedirectResponse

from core.models import db_helper
from core.redis_config import redis_client
from entities.users.schema import (
    SignupRequest,
    VerifyOTPRequest,
    LoginSchema,
    GoogleSignupRequest,
)
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

    return {"id": user.id, "email": user.email, "username": user.username}


@router.get("/google/callback")
async def google_callback(
    response: Response,
    code: str = Query(None),
    error: str = Query(None),
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    print(code)
    if not code:
        print("here")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Code not provided by Google",
        )

    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": os.getenv("GOOGLE_CLIENT_ID"),
        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
        "redirect_uri": os.getenv("GOOGLE_REDIRECT_URI"),
        "grant_type": "authorization_code",
    }

    async with httpx.AsyncClient() as client:
        token_res = await client.post(token_url, data=data)
        if token_res.status_code != 200:
            print("Google Token Error:", token_res.text)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Unauthorized"
            )

        tokens = token_res.json()
        access_token = tokens.get("access_token")

        user_info_url = "https://www.googleapis.com/oauth2/v2/userinfo"
        headers = {"Authorization": f"Bearer {access_token}"}

        user_res = await client.get(user_info_url, headers=headers)

        if user_res.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Unauthorized"
            )

        user_info = user_res.json()

        email = user_info.get("email")
        username = user_info.get("name")
        data = {
            "email": email,
            "username": username,
        }

        try:
            user = await service.register_user_without_otp(
                GoogleSignupRequest.model_validate(data), session
            )
            await crud.verify_user(session, user)
        except IntegrityError as e:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=e.__notes__[0]
            )

        frontend_redirect_url = "http://localhost:3000/"
        redirect_response = RedirectResponse(url=frontend_redirect_url)

        redirect_response.set_cookie(
            key="email",
            value=email,
            httponly=False,
            samesite="lax",
            secure=False,
        )
        redirect_response.set_cookie(
            key="username", value=username, httponly=False, samesite="lax", secure=False
        )

        return redirect_response
