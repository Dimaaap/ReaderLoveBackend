from pathlib import Path
from datetime import timedelta, datetime, timezone
import os

from jwt import ExpiredSignatureError, InvalidTokenError
from platformdirs import user_log_dir
from pwdlib import PasswordHash
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status, Response
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from jose import jwt, JWTError
from starlette.responses import RedirectResponse

from core.models.users import RegisterWays
from custom_errors.user_existing_error import UserExistingError
from utils.otp import generate_random_otp
from . import crud
from .schema import SignupRequest, CreateUser, GoogleSignupRequest
from core.models import User

password_context = PasswordHash.recommended()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = os.getenv("JWT_ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_EXPIRED_MINUTES"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_EXPIRED_DAYS"))

mail_config = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    MAIL_FROM=os.getenv("MAIL_FROM"),
    MAIL_PORT=os.getenv("MAIL_PORT"),
    MAIL_SERVER=os.getenv("MAIL_SERVER"),
    MAIL_STARTTLS=os.getenv("MAIL_STARTTLS") == "True",
    MAIL_SSL_TLS=os.getenv("MAIL_SSL_BF") == "True",
    USE_CREDENTIALS=os.getenv("USE_CREDENTIALS") == "True",
    VALIDATE_CERTS=os.getenv("VALIDATE_CERTS") == "True",
    TEMPLATE_FOLDER=TEMPLATES_DIR,
)


def create_token(data: dict, expires_delta: timedelta) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


def generate_auth_tokens(user_id: str) -> tuple[str, str]:
    access_token = create_token(
        data={"sub": user_id, "type": "access"},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    refresh_token = create_token(
        data={"sub": user_id, "type": "refresh"},
        expires_delta=timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    )

    return access_token, refresh_token


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
        return False

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
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        expire_timestamp = payload.get("exp")

        if not expire_timestamp:
            return

        current_timestamp = int(datetime.now(timezone.utc).timestamp())
        ttl = expire_timestamp - current_timestamp

        if ttl > 0:
            await redis_client.set(f"blacklist:{token}", "1", ex=ttl)
    except JWTError:
        pass


async def is_token_blacklisted(token: str, redis_client) -> bool:
    if not token:
        return False

    exists = await redis_client.exists(f"blacklist:{token}")
    return bool(exists)


def get_user_id_from_token(token: str, expected_type: str = "access") -> str:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

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
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        samesite="lax",
        secure=False,
        path=path if path else "/",
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
    )


def delete_auth_cookies(response: Response) -> None:
    response.delete_cookie(
        key="access_token", httponly=True, samesite="lax", secure=False
    )

    response.delete_cookie(
        key="refresh_token", httponly=True, samesite="lax", secure=False
    )


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

    if not user:
        raise invalid_credentials_exception

    is_password_correct = password_context.verify(data.password, user.password_hash)

    if not is_password_correct:
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

    return await register_user_with_github(user_data, session, email)


async def register_user_with_github(user_data, session: AsyncSession, email: str):
    access_token = refresh_token = None

    try:
        user = await register_user_without_otp(
            GoogleSignupRequest.model_validate(user_data), session, RegisterWays.GITHUB
        )

        await crud.verify_user(session, user)
        access_token, refresh_token = generate_auth_tokens(user.id)

    except IntegrityError:

        user = await crud.get_user_by_id(session, email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error",
            )
    frontend_redirect_url = "http://localhost:3000/"
    redirect_response = RedirectResponse(url=frontend_redirect_url)

    set_auth_cookies(
        redirect_response, access_token, refresh_token, path="/auth/refresh"
    )
    redirect_response.set_cookie(
        key="username",
        value=user_data.get("username"),
        httponly=False,
        samesite="lax",
        secure=False,
    )

    return redirect_response


async def register_user_with_google(data, session: AsyncSession):
    try:
        user = await register_user_without_otp(
            GoogleSignupRequest.model_validate(data), session, RegisterWays.GOOGLE
        )

        await crud.verify_user(session, user)
        access_token, refresh_token = generate_auth_tokens(user.id)
    except IntegrityError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=e.__notes__[0])

    frontend_redirect_url = "http://localhost:3000/"
    redirect_response = RedirectResponse(url=frontend_redirect_url)
    if access_token and refresh_token:
        set_auth_cookies(
            redirect_response, access_token, refresh_token, path="/auth/refresh"
        )

    return redirect_response
