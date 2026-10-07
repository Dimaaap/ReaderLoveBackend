from datetime import datetime, timezone, timedelta

from loguru import logger
from sqlalchemy import select, delete, false, or_
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from entities.users.schema import (
    CreateUser,
    UpdateUser,
    UpdateUserPartial,
    UpdateUserSettings,
    UserByUsernameSchema,
)

from core.models import (
    User,
    UserSettings,
    Book,
    UserBookAssociation,
    UserFriends,
    ReadingSession,
)


async def get_user_by_email(session: AsyncSession, email: str) -> User:
    statement = select(User).where(User.email == email)
    result = await session.execute(statement)
    return result.scalar_one_or_none()


async def get_user_by_id(session: AsyncSession, id: str) -> User:
    statement = (
        select(User)
        .options(selectinload(User.settings), selectinload(User.following))
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
            selectinload(User.following),
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
        logger.error(f"User with username was not found")
        return None

    logger.info(f"User with username {username} was found")
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

    logger.info(f"Update user with data: {user_update}")

    await session.commit()
    await session.refresh(user)
    return user


async def follow_user(
    session: AsyncSession, current_user_id: str, target_user_id: str
) -> bool:
    if current_user_id == target_user_id:
        logger.warning(f"User { current_user_id } attempted to follow themselves")
        return False

    statement = select(UserFriends).where(
        UserFriends.user_id == current_user_id, UserFriends.friend_id == target_user_id
    )
    result = await session.execute(statement)
    existing_follow = result.scalar_one_or_none()

    if existing_follow:
        logger.info(
            f"User { current_user_id } is already following { target_user_id }."
        )
        return False

    new_follow = UserFriends(user_id=current_user_id, friend_id=target_user_id)
    session.add(new_follow)
    await session.commit()

    logger.info(f"User { current_user_id } successfully followed { target_user_id }")
    return True


async def unfollow_user(
    session: AsyncSession, current_user_id: str, target_user_id: str
) -> bool:
    statement = delete(UserFriends).where(
        UserFriends.user_id == current_user_id, UserFriends.friend_id == target_user_id
    )

    result = await session.execute(statement)
    await session.commit()

    if result.rowcount > 0:
        logger.info(f"User { current_user_id } unfollowed { target_user_id }")
        return True

    logger.info(
        f"Follow relation between { current_user_id } and { target_user_id } not found"
    )
    return False


async def toggle_follow_user(
    session: AsyncSession, current_user_id: str, target_user_id: str
) -> bool:
    if current_user_id == target_user_id:
        return False

    statement = select(UserFriends).where(
        UserFriends.user_id == current_user_id, UserFriends.friend_id == target_user_id
    )
    result = await session.execute(statement)
    existing_follow = result.scalar_one_or_none()

    if existing_follow:
        await session.delete(existing_follow)
        await session.commit()
        logger.info(f"User { current_user_id } unfollowed { target_user_id }")
        return False
    else:
        new_follow = UserFriends(user_id=current_user_id, friend_id=target_user_id)
        session.add(new_follow)
        await session.commit()
        logger.info(f"User { current_user_id } followed { target_user_id }")
        return True


async def get_user_following(
    session: AsyncSession,
    target_user_id: str,
    current_user_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:

    is_following_subquery = (
        select(1)
        .select_from(UserFriends)
        .where(
            UserFriends.user_id == current_user_id,
            UserFriends.friend_id == User.id,
        )
        .exists()
        .correlate_except(UserFriends)
        if current_user_id
        else false()
    )

    statement = (
        select(User, is_following_subquery.label("is_following"))
        .join(UserFriends, UserFriends.friend_id == User.id)
        .where(UserFriends.user_id == target_user_id)
        .limit(limit)
        .offset(offset)
    )

    result = await session.execute(statement)

    following_list = []
    for user, is_following in result.all():
        user_dict = {
            "id": user.id,
            "username": user.username,
            "avatar": user.avatar,
            "avatar_color": user.avatar_color,
            "about_info": user.about_info,
            "is_following": bool(is_following),
        }
        following_list.append(user_dict)

    return following_list


async def get_following_reading_sessions(
    session: AsyncSession,
    user_id: str,
    days: int = 30,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    time_threshold = datetime.now(timezone.utc) - timedelta(days=days)

    statement = (
        select(
            ReadingSession, User, UserBookAssociation.status.label("user_book_status")
        )
        .join(User, ReadingSession.user_id == User.id)
        .join(UserFriends, UserFriends.friend_id == User.id)
        .options(
            joinedload(ReadingSession.book), selectinload(ReadingSession.reactions)
        )
        .outerjoin(
            UserBookAssociation,
            (UserBookAssociation.user_id == user_id)
            & (UserBookAssociation.book_id == ReadingSession.book_id),
        )
        .where(
            UserFriends.user_id == user_id, ReadingSession.started_at >= time_threshold
        )
        .order_by(ReadingSession.started_at.desc())
        .limit(limit)
        .offset(offset)
    )

    result = await session.execute(statement)

    feed_items = []
    for reading_session, user, user_book_status in result.all():
        reactions_count: dict[str, int] = {}
        user_reactions: list[str] = []

        db_reactions = getattr(reading_session, "reactions", []) or []

        for reaction in db_reactions:
            reactions_count[reaction.emoji] = reactions_count.get(reaction.emoji, 0) + 1
            if user_id and str(reaction.user_id) == str(user_id):
                user_reactions.append(reaction.emoji)

        item = {
            "id": reading_session.id,
            "start_page": getattr(reading_session, "start_page", None),
            "end_page": getattr(reading_session, "end_page", None),
            "started_at": getattr(reading_session, "started_at", None),
            "ended_at": getattr(reading_session, "ended_at", None),
            "is_tracked": getattr(reading_session, "is_tracked", None),
            "book": (
                {
                    "id": reading_session.book.id,
                    "title": reading_session.book.title,
                    "slug": reading_session.book.slug,
                    "megogo_book_link": reading_session.book.megogo_book_link,
                    "description": reading_session.book.description,
                    "image_link": reading_session.book.image_link,
                    "user_status": user_book_status.value if user_book_status else None,
                }
                if getattr(reading_session, "book", None)
                else None
            ),
            "user": {
                "id": user.id,
                "username": user.username,
                "avatar": user.avatar,
                "avatar_color": user.avatar_color,
            },
            "reactions": reactions_count,
            "user_reactions": user_reactions,
        }

        feed_items.append(item)

    return feed_items


async def get_user_followers(
    session: AsyncSession,
    target_user_id: str,
    current_user_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:

    is_following_subquery = (
        select(1)
        .select_from(UserFriends)
        .where(
            UserFriends.user_id == current_user_id,
            UserFriends.friend_id == User.id,
        )
        .exists()
        .correlate_except(UserFriends)
        if current_user_id
        else false()
    )

    statement = (
        select(User, is_following_subquery.label("is_following"))
        .join(UserFriends, UserFriends.user_id == User.id)
        .where(UserFriends.friend_id == target_user_id)
        .limit(limit)
        .offset(offset)
    )
    result = await session.execute(statement)

    followers_list = []
    for user, is_following in result.all():
        user_dict = {
            "id": user.id,
            "username": user.username,
            "avatar": user.avatar,
            "avatar_color": user.avatar_color,
            "about_info": user.about_info,
            "is_following": bool(is_following),
        }
        followers_list.append(user_dict)

    return followers_list


async def is_following_user(
    session: AsyncSession, current_user_id: str, target_user_id: str
) -> bool:
    statement = (
        select(1)
        .select_from(UserFriends)
        .where(
            UserFriends.user_id == current_user_id,
            UserFriends.friend_id == target_user_id,
        )
        .exists()
        .select()
    )

    result = await session.execute(statement)
    return bool(result.scalar())


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
    logger.info(f"User { user.username } update avatar { user.avatar }")

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
    logger.info(f"Updated user settings for user {user.username}")

    return user.settings


async def search_users(
    session: AsyncSession,
    query: str,
    current_user_id: str | None = None,
    limit: int = 20,
) -> list[dict]:

    if not query or not query.strip():
        return []

    search_pattern = f"%{query.strip()}%"

    is_following_subquery = (
        select(1)
        .select_from(UserFriends)
        .where(
            UserFriends.user_id == current_user_id,
            UserFriends.friend_id == User.id,
        )
        .exists()
        .correlate_except(UserFriends)
        if current_user_id
        else false()
    )

    statement = (
        select(User, is_following_subquery.label("is_following"))
        .where(
            or_(User.username.ilike(search_pattern), User.email.ilike(search_pattern))
        )
        .limit(limit)
    )

    if current_user_id:
        statement = statement.where(User.id != current_user_id)

    result = await session.execute(statement)

    users_with_status = []
    for user, is_following in result.all():
        user_dict = {
            "id": user.id,
            "username": user.username,
            "avatar": user.avatar,
            "avatar_color": user.avatar_color,
            "about_info": user.about_info,
            "is_following": bool(is_following),
        }
        users_with_status.append(user_dict)

    return users_with_status


async def delete_avatar(session: AsyncSession, user: User) -> User:
    user.avatar = None
    logger.info(f"Deleted avatar for user {user.email}")

    await session.commit()
    await session.refresh(user)

    return user


async def verify_user(session: AsyncSession, user: User) -> User:
    user.is_verified = True
    await session.commit()
    return user
