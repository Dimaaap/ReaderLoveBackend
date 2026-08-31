from datetime import timedelta, datetime, timezone
import os
import aiofiles
from uuid import uuid4
from loguru import logger
from PIL import Image
from urllib.parse import quote

from jwt import ExpiredSignatureError, InvalidTokenError
from pwdlib import PasswordHash
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status, Response, UploadFile
from fastapi_mail import FastMail, MessageSchema, MessageType
from jose import jwt, JWTError
from starlette.responses import RedirectResponse

from core.models.users import RegisterWays
from custom_errors.user_existing_error import UserExistingError
from utils.otp import generate_random_otp
from . import crud
from .schema import SignupRequest, CreateUser, GoogleSignupRequest
from core.models import User
from .settings import settings
from .mail import mail_config

password_context = PasswordHash.recommended()


def create_token(data: dict, expires_delta: timedelta) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def generate_auth_tokens(user_id: str) -> tuple[str, str]:
    access_token = create_token(
        data={"sub": user_id, "type": "access"},
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )

    refresh_token = create_token(
        data={"sub": user_id, "type": "refresh"},
        expires_delta=timedelta(days=settings.refresh_token_expire_days),
    )
    logger.info("Generated access and refresh tokens")
    return access_token, refresh_token


async def save_avatar(file: UploadFile, old_avatar: str | None) -> str:
    if file.content_type not in settings.allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported image format"
        )

    os.makedirs(settings.avatar_dir, exist_ok=True)
    filename = f"{uuid4().hex}.webp"

    path = os.path.join(settings.avatar_dir, filename)

    content = await file.read()

    if len(content) > settings.avatar_max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Maximum avatar file is 5MB"
        )

    temp_path = path + ".tmp"

    async with aiofiles.open(temp_path, "wb") as f:
        await f.write(content)

    image = Image.open(temp_path)
    image.thumbnail((512, 512))
    image.save(path, "WEBP", quality=90)

    os.remove(temp_path)

    if old_avatar:
        old_path = old_avatar.lstrip("/")

        if os.path.exists(old_path):
            os.remove(old_path)

    return f"/media/avatars/{filename}"


async def delete_avatar(path: str | None):
    if not path:
        return
    try:
        os.remove(path)
        logger.info(f"Deleted avatar {path}")
    except FileNotFoundError:
        pass


async def verify_otp(
    email: str, input_otp: str, session: AsyncSession, redis_client
) -> User:
    redis_key = f"otp:{email}"
    saved_otp = await redis_client.get(redis_key)

    if not saved_otp:
        raise ValueError("Expired OTP")

    if saved_otp != input_otp:
        raise ValueError("Invalid OTP")

    user = await crud.get_user_by_email(session, email)

    if not user:
        raise ValueError("Invalid email")
    user = await crud.verify_user(session, user)
    await redis_client.delete(redis_key)

    return user


async def send_otp_email(email: str, username: str, otp: str):
    message = MessageSchema(
        subject="Your verification code",
        recipients=[email],
        template_body={"username": username, "otp": otp},
        subtype=MessageType.html,
    )

    fm = FastMail(mail_config)
    logger.info(f"Email with verification code { message } was sent to email { email }")
    await fm.send_message(message, template_name="otp-email.html")


async def send_reset_password_email(email: str, username: str, otp: str):
    message = MessageSchema(
        subject="Forgot your password?",
        recipients=[email],
        template_body={"username": username, "otp": otp},
        subtype=MessageType.html,
    )

    fm = FastMail(mail_config)
    await fm.send_message(message, template_name="forgot-password.html")


async def update_user_password(session: AsyncSession, email: str, new_password: str):
    user = await crud.get_user_by_email(session, email)
    if not user:
        logger.error(f"User with username {email} was not found")
        return False
    logger.info(f"Get user with email {email}")

    hashed_password = password_context.hash(new_password)
    user.password_hash = hashed_password

    await session.commit()
    return True


async def register_user(data: SignupRequest, session: AsyncSession, redis_client):
    existing = await crud.get_user_by_email(session, str(data.email))

    if existing:
        raise UserExistingError()

    hashed = password_context.hash(data.password)
    create_user_data = {
        "username": data.username,
        "email": data.email,
        "password_hash": hashed,
    }
    user = await crud.create_user(session, CreateUser.model_validate(create_user_data))

    otp = generate_random_otp()
    await redis_client.set(f"otp:{user.email}", otp, ex=300)
    return user, otp


async def register_user_without_otp(
    data: GoogleSignupRequest, session: AsyncSession, register_way
):
    existing = await crud.get_user_by_email(session, str(data.email))

    if existing:
        raise UserExistingError()

    hashed = None
    create_user_data = {
        "username": data.username,
        "email": data.email,
        "password_hash": hashed,
        "register_way": register_way,
    }

    user = await crud.create_user(session, CreateUser.model_validate(create_user_data))
    return user


async def add_token_to_blacklist(token: str, redis_client):
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        expire_timestamp = payload.get("exp")

        if not expire_timestamp:
            return

        current_timestamp = int(datetime.now(timezone.utc).timestamp())
        ttl = expire_timestamp - current_timestamp

        if ttl > 0:
            await redis_client.set(f"blacklist:{token}", "1", ex=ttl)

        logger.info(f"Added token to blacklist {token}")
    except JWTError:
        pass


async def is_token_blacklisted(token: str, redis_client) -> bool:
    if not token:
        return False

    exists = await redis_client.exists(f"blacklist:{token}")
    return bool(exists)


def get_user_id_from_token(token: str, expected_type: str = "access") -> str:
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )

        token_type = payload.get("type")
        if token_type != expected_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token type. Expected {expected_type}, got {token_type}",
            )

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
            )

        return user_id

    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired"
        )
    except (
        JWTError,
        InvalidTokenError,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )


def try_get_user_id_from_token(token: str, expected_type: str = "access") -> str | None:
    user_id = None

    try:
        user_id = get_user_id_from_token(token, expected_type)
    except HTTPException as e:
        if e.status_code == status.HTTP_401_UNAUTHORIZED:
            user_id = None
    return user_id


def set_auth_cookies(
    response: Response, access_token: str, refresh_token: str, path: str = None
) -> None:
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=settings.access_token_expire_minutes * 60,
    )

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        samesite="lax",
        secure=False,
        path=path if path else "/",
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
    )


def delete_auth_cookies(response: Response) -> None:
    response.delete_cookie(
        key="access_token", httponly=True, samesite="lax", secure=False
    )

    response.delete_cookie(
        key="refresh_token", httponly=True, samesite="lax", secure=False
    )
    logger.info("Deleted tokens from cookies")


async def refresh_tokens(refresh_token: str, response: Response):
    user_id = get_user_id_from_token(refresh_token, expected_type="refresh")

    new_access, new_refresh = generate_auth_tokens(user_id)

    set_auth_cookies(response, access_token=new_access, refresh_token=new_refresh)

    return user_id


async def authenticate_user(data: SignupRequest, session: AsyncSession) -> User:
    user = await crud.get_user_by_email(session, str(data.email))

    invalid_credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Неправильний email або пароль"
    )

    logger.info(f"Invalidate credentials for user {data.email}")

    if not user:
        logger.error(invalid_credentials_exception)
        raise invalid_credentials_exception

    is_password_correct = password_context.verify(data.password, user.password_hash)

    if not is_password_correct:
        logger.error(f"Password for user {data.email} is incorrenct")
        raise invalid_credentials_exception

    return user


async def add_github_email(client, email, user_headers: dict):
    emails_res = await client.get(
        "https://api.github.com/user/emails",
        headers=user_headers,
    )

    if emails_res.status_code == 200:
        email_list = emails_res.json()

        for e in email_list:
            if e.get("primary") and e.get("verified"):
                email = e.get("email")
                break
        if not email and email_list:
            email = email_list[0].get("email")
    return email


async def google_response(client, token_url: str, data: dict, session: AsyncSession):
    token_res = await client.post(token_url, data=data)

    if token_res.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Unauthorized"
        )

    tokens = token_res.json()
    access_token = tokens.get("access_token")

    user_info_url = "https://www.googleapis.com/oauth2/v2/userinfo"
    headers = {"Authorization": f"Bearer {access_token}"}
    user_res = await client.get(user_info_url, headers=headers)

    if user_res.status_code != 200:
        logger.error(f"Failed to login with Google")
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

    logger.info(f"Try to register user with Google with data {data}")

    return await register_user_with_google(data, session)


async def github_response(
    client, token_url: str, data: dict, headers: dict, session: AsyncSession
):
    token_res = await client.post(token_url, data=data, headers=headers)

    if token_res.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Github auth failed"
        )

    tokens = token_res.json()
    github_access_token = tokens.get("access_token")

    if not github_access_token:
        logger.error("Failed to get GitHub access token")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to get Github access token",
        )

    user_headers = {
        "Authorization": f"token {github_access_token}",
        "Accept": "application/vnd.github.v3+json",
    }

    user_res = await client.get("https://api.github.com/user", headers=user_headers)

    if user_res.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to get GitHub info"
        )

    user_info = user_res.json()
    username = user_info.get("login")
    email = user_info.get("email")

    if not email:
        email = await add_github_email(client, email, user_headers)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is required but not provided by Github",
        )
    user_data = {
        "email": email,
        "username": username,
    }

    logger.info(f"Try to register user with GitHub with data {user_data}")

    return await register_user_with_github(user_data, session, email)


async def register_user_with_github(user_data, session: AsyncSession, email: str):
    username = user_data.get("username")
    user = await crud.get_user_by_email(session, str(email))

    if not user:
        try:
            user = await register_user_without_otp(
                GoogleSignupRequest.model_validate(user_data),
                session,
                RegisterWays.GITHUB,
            )

            await crud.verify_user(session, user)

        except (IntegrityError, UserExistingError):
            logger.error("Database error")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error",
            )

    access_token, refresh_token = generate_auth_tokens(user.id)
    frontend_redirect_url = "http://localhost:3000/"
    redirect_response = RedirectResponse(url=frontend_redirect_url)

    set_auth_cookies(
        redirect_response, access_token, refresh_token, path="/auth/refresh"
    )

    safe_username = quote(username) if username else ""

    redirect_response.set_cookie(
        key="username",
        value=safe_username,
        httponly=False,
        samesite="lax",
        secure=False,
    )
    logger.info(f"Try to register user with GitHub with data {user_data}")

    return redirect_response


async def register_user_with_google(data, session: AsyncSession):
    email = data.get("email")
    username = data.get("username")

    user = await crud.get_user_by_email(session, str(email))
    logger.info(f"Try to register user with Google {user.username}")

    if not user:
        try:
            user = await register_user_without_otp(
                GoogleSignupRequest.model_validate(data), session, RegisterWays.GOOGLE
            )

            await crud.verify_user(session, user)
        except (IntegrityError, UserExistingError) as e:
            logger.error(e.__notes__[0])
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=e.__notes__[0]
            )
    access_token, refresh_token = generate_auth_tokens(user.id)

    frontend_redirect_url = "http://localhost:3000/"
    redirect_response = RedirectResponse(url=frontend_redirect_url)
    if access_token and refresh_token:
        set_auth_cookies(
            redirect_response, access_token, refresh_token, path="/auth/refresh"
        )

    safe_username = quote(username) if username else ""
    logger.info(f"Register user with Google with username {user.username}")

    redirect_response.set_cookie(
        key="username",
        value=safe_username,
        httponly=False,
        samesite="lax",
        secure=False,
    )

    return redirect_response


async def change_password(
    session: AsyncSession, user: User, current_password: str, new_password: str
):
    if not password_context.verify(current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    if current_password == new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different",
        )

    user.password_hash = password_context.hash(new_password)

    logger.info(f"Change password for user {user.username}")

    await session.commit()
    await session.refresh(user)
