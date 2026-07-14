from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from core.models.user_goals import UserGoalCategory, GoalPeriod


class UserGoalBase(BaseModel):
    user_id: str
    target_value: int
    category: UserGoalCategory
    period: GoalPeriod
    icon: str | None = None
    deadline: datetime | None = None
    created_at: datetime | None = None
    is_completed: bool = False


class UserGoalCreate(UserGoalBase): ...


class UserGoalUpdate(UserGoalCreate): ...


class UserGoalUpdatePartial(UserGoalUpdate):
    user_id: str | None = None
    target_value: int | None = None
    category: UserGoalCategory | None = None
    period: GoalPeriod | None = None


class UserInfo(BaseModel):
    username: str
    email: EmailStr

    model_config = ConfigDict(from_attributes=True)


class UserGoalSchema(UserGoalBase):
    id: int
    user: UserInfo
    current_value: int | None = None

    model_config = ConfigDict(from_attributes=True)
