from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from core.models.reading_streak_state import StreakGoalType
from entities.streak_freeze_days.schema import StreakFreezeDaySchema
from entities.reading_streak_milestones.schema import StreakMilestoneSchema
from utils.custom_validators.nanoid_string_validator import NanoIDString


class ReadingStreakBase(BaseModel):
    current_streak: int = Field(0, ge=0)
    best_streak: int = Field(0, ge=0)
    last_active_date: date | None = None
    freezes_available: int = Field(1, ge=0)
    max_freezes: int = Field(2, ge=0, le=30)
    goal_type: StreakGoalType = StreakGoalType.MINUTES
    daily_goal_value: int = Field(15, ge=1, le=1440)


class ReadingStreakCreate(ReadingStreakBase):
    user_id: NanoIDString


class ReadingStreakUpdate(ReadingStreakBase): ...


class ReadingStreakUpdatePartial(BaseModel):
    current_streak: int | None = Field(None, ge=0)
    best_streak: int | None = Field(None, ge=0)
    last_active_date: date | None = None
    freezes_available: int | None = Field(None, ge=0)
    max_freezes: int | None = Field(None, ge=0, le=30)
    goal_type: StreakGoalType | None = None
    daily_goal_value: int | None = Field(None, ge=1, le=1440)


class ReadingStreakGoalUpdate(BaseModel):
    goal_type: StreakGoalType | None = None
    daily_goal_value: int = Field(..., ge=1, le=1440)


class ReadingStreakSchema(ReadingStreakBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: NanoIDString
    updated_at: datetime


class ReadingStreakDetailSchema(ReadingStreakSchema):
    today_progress: int = 0
    is_goal_completed_today: bool = False
    freezes: list[StreakFreezeDaySchema] = []
    milestones: list[StreakMilestoneSchema] = []
