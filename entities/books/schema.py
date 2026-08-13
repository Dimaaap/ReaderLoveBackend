from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from core.models.user_book_association import BookReadStatus
from entities.book_authors.schema import BookAuthorsSchema
from entities.book_genres.schema import BookGenreSchema
from entities.book_reviews.schema import BookReviewSchema


class BookBase(BaseModel):
    isbn: str | None = None
    title: str
    slug: str
    image_link: str
    pages_count: int
    description: str | None = None
    publish_date: str | int | None = None
    language: str | None = None


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
    reviews: list[BookReviewSchema] | None


class BookSchema(BookBase):
    id: int
    genres: list[BookGenreSchema]
    authors: list[BookAuthorsSchema]

    model_config = ConfigDict(from_attributes=True)


class MiniReadingSessionSchema(BaseModel):
    id: int
    start_page: int
    end_page: int | None
    started_at: datetime
    ended_at: datetime | None
    is_tracked: bool = True

    model_config = ConfigDict(from_attributes=True)


class PublisherSchema(BaseModel):
    title: str

    model_config = ConfigDict(from_attributes=True)


class BookDetailSchema(BookSchema):
    publisher: PublisherSchema | None = None
    reviews: list[BookReviewSchema] = []
    reading_sessions_count: int = 0
    read_pages: int = Field(default=0, alias="last_read_page")
    active_session_id: int | None = None
    status: BookReadStatus | None = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class UserBookStatusUpdate(BaseModel):
    status: BookReadStatus
    last_read_page: int | None = 0


class BookSchemaWithSessions(BookDetailSchema):
    weekly_read_pages: int = 0
    recent_sessions: list[MiniReadingSessionSchema] = []
    current_streak: int = 0

    model_config = ConfigDict(from_attributes=True)


class ExportLibraryOptions(BaseModel):
    format: Literal["csv", "json", "pdf"] = Field(default="csv")
    filter_status: Literal[
        "all", "want_to_read", "reading", "finished", "paused", "abandoned"
    ] = Field(default="all")
    include_notes: bool = Field(default=True)


class UserBookItemSchema(BaseModel):
    status: BookReadStatus
    last_read_page: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None
    book: BookSchema

    model_config = ConfigDict(from_attributes=True)


class UserBookSchema(BookSchema):
    status: BookReadStatus | None = None
    last_read_page: int = 0

    model_config = ConfigDict(from_attributes=True)
