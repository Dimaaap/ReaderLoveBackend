from celery import Celery
from celery.schedules import crontab
from core.config import settings

celery_app = Celery(
    "readerlove_worker",
    broker=settings.redis.redis_url,
    backend=settings.redis.redis_url,
    include=["entities.users.tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Kyiv",
    enable_utc=True,
    beat_schedule={
        "send-reading-reminders-every-day-at-20-00": {
            "task": "users.send_daily_reminders_task",
            "schedule": crontab(hour=13, minute=00)
        }
    }
)
