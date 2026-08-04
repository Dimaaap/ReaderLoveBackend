from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from entities.users.schema import (
    CreateUser,
    UpdateUser,
    UpdateUserPartial,
    UpdateUserSettings,
    UserByUsernameSchema,
)

from core.models import User, UserSettings, Book, UserBookAssociation


async def get_user_by_email(session: AsyncSession, email: str) -> User:
    statement = select(User).where(User.email == email)
    result = await session.execute(statement)
    return result.scalar_one_or_none()


async def get_user_by_id(session: AsyncSession, id: str) -> User:
    statement = (
        select(User)
        .options(selectinload(User.settings), selectinload(User.friends))
        .where(
            User.id == id,
        )
    )
    result = await session.execute(statement)
    return result.scalar_one_or_none()


async def get_user_by_username(
    session: AsyncSession, username: str
) -> UserByUsernameSchema | None:
    statement = (
        select(User)
        .options(
            selectinload(User.settings),
            selectinload(User.friends),
            selectinload(User.user_books)
            .selectinload(UserBookAssociation.book)
            .options(
                selectinload(Book.authors),
                selectinload(Book.genres),
            ),
        )
        .where(User.username == username)
    )

    result = await session.execute(statement)
    user = result.scalar_one_or_none()

    if not user:
        return None

    return UserByUsernameSchema.model_validate(user)


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

    user.settings = UserSettings()
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


async def update_user_settings(
    session: AsyncSession, user: User, settings_update: UpdateUserSettings
) -> UserSettings:
    update_data = settings_update.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(user.settings, key, value)

    await session.commit()
    await session.refresh(user.settings)

    return user.settings


async def delete_avatar(session: AsyncSession, user: User) -> User:
    user.avatar = None

    await session.commit()
    await session.refresh(user)

    return user


async def verify_user(session: AsyncSession, user: User) -> User:
    user.is_verified = True
    await session.commit()
    return user
