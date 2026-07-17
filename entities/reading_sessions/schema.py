from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class ReadingSessionBase(BaseModel):
    user_id: str
    book_id: int
    started_at: datetime
    ended_at: datetime | None = None
    start_page: int
    end_page: int | None = None
    is_tracked: bool = True


class ReadingSessionCreate(BaseModel):
    username: str
    book_id: int
    started_at: datetime | None = None
    ended_at: datetime | None = None
    start_page: int
    end_page: int | None = None
    is_tracked: bool = True


class ReadingSessionUpdate(ReadingSessionCreate): ...


class ReadingSessionUpdatePartial(ReadingSessionUpdate):
    username: str | None = None
    book_id: int | None = None
    started_at: datetime | None = None
    start_page: int | None = None


class UserReadingSessionSchema(BaseModel):
    username: str
    email: EmailStr

    model_config = ConfigDict(from_attributes=True)


class BookReadingSessionSchema(BaseModel):
    title: str
    slug: str
    image_link: str
    pages_count: int

    model_config = ConfigDict(from_attributes=True)


class ReadingSessionSchema(ReadingSessionBase):
    id: int

    user: UserReadingSessionSchema
    book: BookReadingSessionSchema

    model_config = ConfigDict(from_attributes=True)
