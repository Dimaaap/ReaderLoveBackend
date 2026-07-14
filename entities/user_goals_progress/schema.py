from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from core.models.user_goals_progress import UserGoalsProgress


class UserGoalProgressBase(BaseModel):
    goal_id: int
    value: int
    log_date: date


class UserGoalProgressCreate(UserGoalProgressBase): ...


class UserGoalProgressUpdate(UserGoalProgressCreate): ...


class UserGoalProgressUpdatePartial(UserGoalProgressUpdate):
    goal_id: int | None = None
    value: int | None = None
    log_date: date | None = None


class GoalInfo(BaseModel):
    target_value: int
    is_completed: bool = False
    deadline: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class UserGoalProgresSchema(UserGoalProgressBase):
    id: int
    goal: GoalInfo

    model_config = ConfigDict(from_attributes=True)
