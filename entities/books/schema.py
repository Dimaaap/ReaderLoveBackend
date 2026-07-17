from datetime import datetime

from pydantic import BaseModel, ConfigDict

from core.models.user_book_association import BookReadStatus
from entities.book_authors.schema import BookAuthorsSchema
from entities.book_genres.schema import BookGenreSchema


class BookBase(BaseModel):
    title: str
    slug: str
    image_link: str
    pages_count: int
    description: str | None = None
    publish_date: str | int | None = None
    language: str | None = None

    authors: list[BookAuthorsSchema]
    genres: list[BookGenreSchema]


class AuthorInsideBook(BaseModel):
    first_name: str
    last_name: str


class BookCreate(BookBase):
    authors: list[AuthorInsideBook]
    genres: list[str]


class BookUpdate(BookCreate): ...


class BookUpdatePartial(BookUpdate):
    title: str | None
    slug: str | None
    image_link: str | None
    pages_count: int | None
    authors: list[BookAuthorsSchema] | None
    genres: list[BookGenreSchema] | None


class BookSchema(BookBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class MiniReadingSessionSchema(BaseModel):
    id: int
    start_page: int
    end_page: int | None
    started_at: datetime
    ended_at: datetime | None
    is_tracked: bool = True

    model_config = ConfigDict(from_attributes=True)


class BookDetailSchema(BookSchema):
    reading_sessions_count: int = 0
    read_pages: int = 0
    active_session_id: int | None = None

    model_config = ConfigDict(from_attributes=True)


class BookSchemaWithSessions(BookDetailSchema):
    weekly_read_pages: int = 0
    recent_sessions: list[MiniReadingSessionSchema] = []
    current_streak: int = 0

    model_config = ConfigDict(from_attributes=True)


class UserBookSchema(BookSchema):
    status: BookReadStatus

    model_config = ConfigDict(from_attributes=True)
