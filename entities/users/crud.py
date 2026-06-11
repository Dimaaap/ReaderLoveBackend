from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from entities.users.schema import CreateUser

from core.models import User


async def get_user_by_email(session: AsyncSession, email: str) -> User:
    statement = select(User).where(User.email == email)
    result = await session.execute(statement)
    return result.scalar_one_or_none()


async def create_user(session: AsyncSession, user_data: CreateUser) -> User:
    user = User(**user_data.model_dump())
    try:
        session.add(user)
        await session.commit()
        await session.refresh(user)
    except IntegrityError as e:
        e.add_note("User with this username already exists")
        raise
    return user


async def verify_user(session: AsyncSession, user: User) -> User:
    user.is_verified = True
    await session.commit()
    return user
