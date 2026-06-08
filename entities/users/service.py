from pathlib import Path
from datetime import timedelta, datetime, timezone
import os
from typing import Iterable

from pwdlib import PasswordHash
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from jose import jwt, JWTError

from custom_errors.user_existing_error import UserExistingError
from utils.otp import generate_random_otp
from . import crud
from .schema import SignupRequest, CreateUser
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
