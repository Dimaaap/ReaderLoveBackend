from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from entities.social_links.schema import (
    SocialLinkSchema,
    SocialLinkCreate,
    SocialLinkUpdate,
    SocialLinkUpdatePartial,
)
from core.models.social_links import SocialLinks


async def get_all_social_links(session: AsyncSession) -> list[SocialLinkSchema]:
    statement = select(SocialLinks)

    result = await session.execute(statement)
    social_links = result.scalars().all()

    return [SocialLinkSchema.model_validate(link) for link in social_links]


async def create_social_link(
    session: AsyncSession, data: SocialLinkCreate
) -> SocialLinkSchema:
    new_social_link = SocialLinks(**data.model_dump())

    session.add(new_social_link)
    await session.commit()
    await session.refresh(new_social_link)

    return SocialLinkSchema.model_validate(new_social_link)


async def get_social_link_by_id(session: AsyncSession, id: int) -> SocialLinks | None:
    statement = select(SocialLinks).where(SocialLinks.id == id)

    result = await session.execute(statement)
    social_link = result.scalar_one_or_none()

    if social_link is None:
        return None

    return social_link


async def update_social_link(
    session: AsyncSession, id: int, data: SocialLinkUpdate
) -> SocialLinkSchema | None:
    statement = select(SocialLinks).where(SocialLinks.id == id)

    result = await session.execute(statement)
    social_link = result.scalar_one_or_none()

    if social_link is None:
        return None

    for key, value in data.model_dump().items():
        setattr(social_link, key, value)

    await session.commit()
    await session.refresh(social_link)

    return SocialLinkSchema.model_validate(social_link)


async def partial_update_social_link(
    session: AsyncSession, id: int, data: SocialLinkUpdatePartial
):
    statement = select(SocialLinks).where(SocialLinks.id == id)
    result = await session.execute(statement)
    social_link = result.scalar_one_or_none()

    if social_link is None:
        return None

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(social_link, key, value)

    await session.commit()
    await session.refresh(social_link)

    return SocialLinkSchema.model_validate(social_link)


async def delete_social_link(session: AsyncSession, id: int) -> bool:
    result = await session.execute(select(SocialLinks).where(SocialLinks.id == id))

    social_link = result.scalar_one_or_none()

    if social_link is None:
        return False

    await session.delete(social_link)
    await session.commit()
    return True
