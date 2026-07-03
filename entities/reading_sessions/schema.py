from datetime import datetime

from pydantic import BaseModel, ConfigDict

from entities.users.schema import UserSchema
from entities.books.schema import BookSchema


class ReadingSessionBase(BaseModel):
    user_id: str
    book_id: int
    started_at: datetime
    ended_at: datetime | None
    start_page: int
    end_page: int | None

    user: UserSchema
    book: BookSchema


class ReadingSessionCreate(ReadingSessionBase): ...


class ReadingSessionUpdate(ReadingSessionCreate): ...


class ReadingSessionUpdatePartial(ReadingSessionUpdate):
    user_id: str | None = None
    book_id: int | None = None
    started_at: datetime | None = None
    start_page: int | None = None
    user: BookAuthorsSchema | None = None
    book: BookSchema | None = None


class ReadingSessionSchema(ReadingSessionBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
