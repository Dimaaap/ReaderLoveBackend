from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

from core.models.user_book_association import BookReadStatus


class UserInSessionSchema(BaseModel):
    username: str
    email: EmailStr
    avatar: str | None = None

    model_config = ConfigDict(from_attributes=True)


class BookInSessionSchema(BaseModel):
    id: int
    title: str
    slug: str
    image_link: str | None = None
    pages_count: int | None = None
    authors: list[str] = []
    rating: float = 0.0
    reviews_count: int = 0
    description: str | None = None

    status: BookReadStatus | None = None
    last_read_page: int = 0

    model_config = ConfigDict(from_attributes=True)

    @field_validator("authors", mode="before")
    @classmethod
    def convert_authors_to_strings(cls, v):
        if isinstance(v, list) and v:
            result = []
            for item in v:
                if isinstance(item, str):
                    result.append(item)
                elif hasattr(item, "last_name"):
                    first_name = getattr(item, "first_name", "") or ""
                    last_name = getattr(item, "last_name", "") or ""
                    full_name = f"{first_name} {last_name}".strip()
                    result.append(full_name)
            return result
        return v


class ReadingSessionBase(BaseModel):
    book_id: int
    start_page: int
    end_page: int | None = None
    is_tracked: bool = True
    comment: str | None = None


class ReadingSessionCreate(ReadingSessionBase):
    username: str
    started_at: datetime | None = None
    ended_at: datetime | None = None


class ReadingSessionUpdate(BaseModel):
    start_page: int | None = None
    end_page: int | None = None
    comment: str | None = None
    is_tracked: bool | None = None
    ended_at: datetime | None = None


class ReadingSessionUpdatePartial(ReadingSessionUpdate): ...


class ReadingSessionSchema(ReadingSessionBase):
    id: int
    user_id: str
    started_at: datetime | None = None
    ended_at: datetime | None = None

    user: UserInSessionSchema
    book: BookInSessionSchema

    reactions: dict[str, int] = {}
    user_reactions: list[str] = []

    model_config = ConfigDict(from_attributes=True)
