import sys

import asyncio
from core.celery_app import celery_app
from entities.users.service import (
    send_daily_reading_reminders,
    send_bulk_book_promotions,
    send_personalized_book_recommendations,
)

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


@celery_app.task(name="users.send_daily_reminders_task")
def senf_daily_reminders_task():
    asyncio.run(send_daily_reading_reminders())


@celery_app.task(name="users.send_bulk_promotions_task")
def send_bulk_promotions_task(subject: str, message_content: str):
    asyncio.run(send_bulk_book_promotions(subject, message_content))


@celery_app.task(name="users.send_personalized_recommendations_task")
def send_personalized_recommendations_task():
    asyncio.run(send_personalized_book_recommendations())
