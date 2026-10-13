from pydantic import BaseModel, ConfigDict
from typing import List, Literal


class StatsMetric(BaseModel):
    current: float | int
    change_percentage: float


class ReadingTimeMetric(BaseModel):
    total_seconds: int
    change_percentage: float


class ChartDataPoint(BaseModel):
    date: str
    pages: int


class UserStatisticsResponse(BaseModel):
    period: Literal["7d", "1m", "3m", "1y", "all"]
    pages_read: StatsMetric
    books_finished: StatsMetric
    pages_per_day: StatsMetric
    reading_time: ReadingTimeMetric
    chart_data: List[ChartDataPoint]

    model_config = ConfigDict(from_attributes=True)
