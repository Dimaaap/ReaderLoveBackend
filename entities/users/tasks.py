import asyncio
from core.celery_app import celery_app
from entities.users.service import send_daily_reading_reminders


@celery_app.task(name="users.send_daily_reminders_task")
def senf_daily_reminders_task():
    asyncio.run(send_daily_reading_reminders())
