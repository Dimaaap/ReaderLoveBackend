from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from core.models.reading_cycle import ReadingCycleStatus


class ReadingCycleBase(BaseModel):
    book_id: int


class ReadingCycleCreate(ReadingCycleBase):
    username: str


class ReadingCycleUpdate(BaseModel):
    status: ReadingCycleStatus | None = None
    last_read_page: int | None = Field(default=None, ge=0)
    last_read_percent: float | None = Field(default=None, ge=0, le=100)
    finished_at: datetime | None = None


class ReadingCycleSchema(ReadingCycleBase):
    id: int
    user_id: str

    read_number: int
    status: ReadingCycleStatus

    last_read_page: int = 0
    last_read_percent: float = 0.0

    started_at: datetime
    finished_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class ReadingCycleWithStatsSchema(ReadingCycleSchema):
    sessions_count: int = 0


class ReadingCycleHistorySchema(BaseModel):
    book_id: int
    total_reads: int
    cycles: list[ReadingCycleWithStatsSchema] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
