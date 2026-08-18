import asyncio
import json
from pathlib import Path

from sqlalchemy import select

from core.models import BookPublisher, db_helper

DATA_FILE = Path(__file__).parent / "data.json"


async def seed_publishers():
    with open(DATA_FILE, "r", encoding="utf-8") as file:
        publishers = json.load(file)
    async with db_helper.session_factory() as session:
        for publisher_data in publishers:
            result = await session.execute(
                select(BookPublisher).where(
                    (BookPublisher.title == publisher_data["title"])
                    | (BookPublisher.slug == publisher_data["slug"])
                )
            )

            existing_publisher = result.scalar_one_or_none()

            if existing_publisher:
                print(f"Пропущено: {publisher_data['title']} (вже існує)")
                continue

            publisher = BookPublisher(
                title=publisher_data["title"], slug=publisher_data["slug"]
            )

            session.add(publisher)
            print(f"Додано: {publisher_data['title']}")
        await session.commit()

    print("Видавництва додані")


if __name__ == "__main__":
    asyncio.run(seed_publishers())
