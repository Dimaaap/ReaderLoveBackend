from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SessionReactionBase(BaseModel):
    emoji: str


class SessionReactionCreate(SessionReactionBase):
    session_id: int
    user_id: int


class SessionReactionUpdate(SessionReactionCreate):
    emoji: str | None = None
    session_id: int | None = None
    user_id: int | None = None


class SessionReactionUpdatePartial(SessionReactionUpdate): ...


class SessionReactionSchema(SessionReactionBase):
    id: int
    session_id: int
    user_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SessionReactionToggleResponse(BaseModel):
    status: str
    emoji: str
    session_id: int
