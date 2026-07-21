from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from entities.users.schema import CreateUser, UpdateUser, UpdateUserPartial

from core.models import User


async def get_user_by_email(session: AsyncSession, email: str) -> User:
    statement = select(User).where(User.email == email)
    result = await session.execute(statement)
    return result.scalar_one_or_none()


async def get_user_by_id(session: AsyncSession, id: str) -> User:
    statement = select(User).where(User.id == id)
    result = await session.execute(statement)
    return result.scalar_one_or_none()


async def update_user(
    session: AsyncSession,
    user: User,
    user_update: UpdateUser | UpdateUserPartial,
    partial: bool = False,
) -> User:
    update_data = user_update.model_dump(
        exclude_unset=partial, exclude={"books", "reading_sessions", "notes", "goals"}
    )

    for key, value in update_data.items():
        setattr(user, key, value)

    await session.commit()
    await session.refresh(user)
    return user


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


async def update_avatar(session: AsyncSession, user: User, avatar: str) -> User:
    user.avatar = avatar

    await session.commit()
    await session.refresh(user)

    return user


async def delete_avatar(session: AsyncSession, user: User) -> User:
    user.avatar = None

    await session.commit()
    await session.refresh(user)

    return user


async def verify_user(session: AsyncSession, user: User) -> User:
    user.is_verified = True
    await session.commit()
    return user
