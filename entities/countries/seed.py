import asyncio
import json
from pathlib import Path

from sqlalchemy import select
from loguru import logger

from core.models import Country, db_helper

DATA_PATH = Path(__file__).resolve().parent / "countries_data.json"


async def seed_countries():
    with DATA_PATH.open("r", encoding="utf-8") as file:
        countries_data = json.load(file)

    async with db_helper.session_factory() as session:
        result = await session.execute(select(Country.code))
        existing_codes = {code for code in result.scalars().all()}

        new_countries = []

        for item in countries_data:
            code = item["code"].upper()

            if code in existing_codes:
                continue

            new_countries.append(
                Country(name=item["name"], code=code, flag=item.get("flag"))
            )

        if not new_countries:
            logger.info("All countries already exist in database")
            return

        session.add_all(new_countries)
        await session.commit()

        logger.info(f"Successfully added {len(new_countries)} countries")


async def main():
    await seed_countries()


if __name__ == "__main__":
    asyncio.run(main())
