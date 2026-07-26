from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import UserSettings
from entities.user_settings.schema import UserSettingsUpdateSchema


async def update_user_settings(
    session: AsyncSession, settings: UserSettings, data: UserSettingsUpdateSchema
) -> UserSettings | None:

    update_data = data.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(settings, key, value)

    await session.commit()
    await session.refresh(settings)

    return settings
