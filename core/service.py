from datetime import date
from loguru import logger

from sqlalchemy import select, and_, func

from entities.users.service import send_reading_reminder_email
from models import db_helper, User, UserSettings, ReadingSession



async def send_daily_reading_reminders():
    async with db_helper.session_factory() as session:
        today = date.today()

        statement = (
            select(User)
            .join(UserSettings, User.id == UserSettings.user_id)
            .where(UserSettings.reading_reminders == True)
        )

        result = await session.execute(statement)
        users = result.scalars().all()

        for user in users:
            session_statement = select(ReadingSession).where(
                and_(
                    ReadingSession.user_id == user.id,
                    func.date(ReadingSession.started_at) == today,
                )
            )

            session_res = await session.execute(session_statement)
            today_sessions = session_res.scalars().all()

            if not today_sessions and user.email:
                try:
                    await send_reading_reminder_email(str(user.email), user.username)
                except Exception as e:
                    logger.error(
                        f"Failed to send reading reminder to {user.email}: {e}"
                    )
