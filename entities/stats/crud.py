from datetime import datetime, timedelta, timezone
from sqlalchemy import select, func, case, desc
from sqlalchemy.ext.asyncio import AsyncSession
from core.models import ReadingSession, UserBookAssociation, User
from core.models.user_book_association import BookReadStatus


def calculate_percentage_change(current: float, prev: float) -> float:
    if prev == 0:
        return 100.0 if current > 0 else 0.0
    return round(((current - prev) / prev) * 100, 1)


async def get_user_reading_statistics(
    session: AsyncSession, username: str, period: str
) -> dict | None:
    user_statement = select(User.id).where(User.username == username)
    user_res = await session.execute(user_statement)
    user_id = user_res.scalar_one_or_none()

    if not user_id:
        return None

    now = datetime.now(timezone.utc)

    period_days_map = {"7d": 7, "1m": 30, "3m": 90, "1y": 365, "all": 36_500}
    days = period_days_map.get(period, 90)

    current_start = now - timedelta(days=days)
    previous_start = current_start - timedelta(days=days)

    pages_current_expression = func.coalesce(
        func.sum(
            case(
                (
                    ReadingSession.end_page >= ReadingSession.start_page,
                    ReadingSession.end_page - ReadingSession.start_page,
                ),
                else_=0,
            )
        ),
        0,
    )
    pages_current_statement = select(pages_current_expression).where(
        ReadingSession.user_id == user_id, ReadingSession.started_at >= current_start
    )

    pages_current = (await session.execute(pages_current_statement)).scalar_one()

    pages_prev_stmt = select(pages_current_expression).where(
        ReadingSession.user_id == user_id,
        ReadingSession.started_at >= previous_start,
        ReadingSession.started_at < current_start,
    )
    pages_prev = (await session.execute(pages_prev_stmt)).scalar_one()
    pages_change = calculate_percentage_change(pages_current, pages_prev)

    books_current_stmt = select(func.count(UserBookAssociation.book_id)).where(
        UserBookAssociation.user_id == user_id,
        UserBookAssociation.status == BookReadStatus.FINISHED,
        UserBookAssociation.updated_at >= current_start,
    )
    books_current = (await session.execute(books_current_stmt)).scalar_one()

    books_prev_stmt = select(func.count(UserBookAssociation.book_id)).where(
        UserBookAssociation.user_id == user_id,
        UserBookAssociation.status == BookReadStatus.FINISHED,
        UserBookAssociation.updated_at >= previous_start,
        UserBookAssociation.updated_at < current_start,
    )
    books_prev = (await session.execute(books_prev_stmt)).scalar_one()
    books_change = calculate_percentage_change(books_current, books_prev)

    duration_expr = func.coalesce(
        func.sum(
            case(
                (
                    ReadingSession.ended_at.isnot(None),
                    func.extract(
                        "epoch", ReadingSession.ended_at - ReadingSession.started_at
                    )
                    - ReadingSession.total_paused_duration,
                ),
                else_=0,
            )
        ),
        0,
    )

    time_current_stmt = select(duration_expr).where(
        ReadingSession.user_id == user_id, ReadingSession.started_at >= current_start
    )
    time_current_seconds = int((await session.execute(time_current_stmt)).scalar_one())

    time_prev_stmt = select(duration_expr).where(
        ReadingSession.user_id == user_id,
        ReadingSession.started_at >= previous_start,
        ReadingSession.started_at < current_start,
    )
    time_prev_seconds = int((await session.execute(time_prev_stmt)).scalar_one())
    time_change = calculate_percentage_change(time_current_seconds, time_prev_seconds)

    chart_stmt = (
        select(
            func.date(ReadingSession.started_at).label("session_date"),
            func.sum(
                case(
                    (
                        ReadingSession.end_page >= ReadingSession.start_page,
                        ReadingSession.end_page - ReadingSession.start_page,
                    ),
                    else_=0,
                )
            ).label("total_pages"),
        )
        .where(
            ReadingSession.user_id == user_id,
            ReadingSession.started_at >= current_start,
        )
        .group_by(func.date(ReadingSession.started_at))
        .order_by("session_date")
    )

    chart_res = await session.execute(chart_stmt)
    chart_data = [
        {
            "date": row.session_date.strftime("%b %d") if row.session_date else "",
            "pages": int(row.total_pages or 0),
        }
        for row in chart_res.all()
    ]

    effective_days = (
        max(days, 1) if period != "all" else max((now - current_start).days, 1)
    )
    pages_per_day_current = round(pages_current / effective_days, 1)

    return {
        "period": period,
        "pages_read": {
            "current": int(pages_current),
            "change_percentage": pages_change,
        },
        "books_finished": {
            "current": int(books_current),
            "change_percentage": books_change,
        },
        "pages_per_day": {
            "current": pages_per_day_current,
            "change_percentage": pages_change,
        },
        "reading_time": {
            "total_seconds": time_current_seconds,
            "change_percentage": time_change,
        },
        "chart_data": chart_data,
    }
