from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from core.models.streak_freeze_days import StreakFreezeSource
from utils.custom_validators.nanoid_string_validator import NanoIDString


class StreakFreezeDayBase(BaseModel):
    frozen_date: date
    source: StreakFreezeSource = StreakFreezeSource.AUTOMATIC


class StreakFreezeDayCreate(StreakFreezeDayBase):
    user_id: NanoIDString
    streak_id: int = Field(..., ge=1)


class StreakFreezeDayUpdate(StreakFreezeDayBase):
    streak_id: int = Field(..., ge=1)


class StreakFreezeDayUpdatePartial(BaseModel):
    frozen_date: date | None = None
    source: StreakFreezeSource | None = None


class StreakFreezeDaySchema(StreakFreezeDayBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: NanoIDString
    streak_id: int
    created_at: datetime
