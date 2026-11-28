from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from utils.custom_validators.nanoid_string_validator import NanoIDString


class StreakMilestoneBase(BaseModel):
    milestone_days: int = Field(..., ge=1)
    is_celebrated: bool = False
    shared_in_app: bool = False
    celebrated_at: datetime | None = None


class StreakMilestoneCreate(StreakMilestoneBase):
    user_id: NanoIDString | str
    streak_id: int = Field(..., ge=1)


class StreakMilestoneUpdate(StreakMilestoneBase):
    streak_id: int = Field(..., ge=1)


class StreakMilestoneUpdatePartial(BaseModel):
    milestone_days: int | None = Field(None, ge=1)
    is_celebrated: bool | None = None
    shared_in_app: bool | None = None
    celebrated_at: datetime | None = None


class StreakMilestoneSchema(StreakMilestoneBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: NanoIDString
    streak_id: int
    reached_at: datetime
