from datetime import timedelta, date
from typing import Sequence


def calculate_streak(reading_dates: Sequence[date]) -> int:
    if not reading_dates:
        return 0
    today = date.today()
    yesterday = today - timedelta(days=1)

    if reading_dates[0] != today and reading_dates[0] != yesterday:
        return 0

    streak = 0
    current_check = reading_dates[0]

    for d in reading_dates:
        if d == current_check:
            streak += 1
            current_check -= timedelta(days=1)
        elif d < current_check:
            break
    return streak
