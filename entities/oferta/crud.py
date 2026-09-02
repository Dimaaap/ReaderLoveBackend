from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from entities.oferta.schema import (
    OfertaSchema,
    OfertaCreate,
)

from core.models import Oferta


async def get_last_oferta(session: AsyncSession) -> OfertaSchema:
    statement = select(Oferta)

    result = await session.execute(statement)
    oferta = result.scalar_one_or_none()
    logger.info("Try to get oferta")

    if oferta is None:
        logger.error("Failed to get oferta")
        return oferta

    return OfertaSchema.model_validate(oferta)


async def create_or_update_oferta(
    session: AsyncSession, oferta_data: OfertaCreate
) -> OfertaSchema:
    statement = select(Oferta).limit(1)

    result = await session.execute(statement)
    oferta = result.scalar_one_or_none()
    logger.info(f"Try to update or delete oferta {oferta_data}")

    if oferta is None:
        logger.info(f"Oferta is none. Create a new oferta")
        oferta = Oferta(html_code=oferta_data.html_code)
        session.add(oferta)
    else:
        logger.info(f"Oferta exista. Update oferta")
        oferta.html_code = oferta_data.html_code

    await session.commit()
    await session.refresh(oferta)

    return OfertaSchema.model_validate(oferta)


async def delete_oferta(session: AsyncSession):
    result = await session.execute(select(Oferta))

    oferta = result.scalar_one_or_none()
    logger.info("Try to delete oferta")
    if oferta is None:
        logger.error(f"Failed to delete oferta")
        return False

    await session.delete(oferta)
    await session.commit()
    return True
