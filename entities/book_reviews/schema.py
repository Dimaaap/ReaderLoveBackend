from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class BookReviewBase(BaseModel):
    rating: int
    text: str | None = None
    is_spoiler: bool = False

    book_id: int
    user_id: str

    created_at: datetime | None = None


class BookReviewCreate(BaseModel):
    rating: int
    text: str | None = None
    is_spoiler: bool = False
    book_id: int
    username: str


class BookReviewUpdate(BookReviewBase): ...


class BookReviewUpdatePartial(BookReviewUpdate):
    rating: int | None = None


class BookBookReviewSchema(BaseModel):
    title: str
    slug: str
    image_link: str
    pages_count: int

    model_config = ConfigDict(from_attributes=True)


class UserBookReviewSchema(BaseModel):
    username: str
    email: EmailStr

    model_config = ConfigDict(from_attributes=True)


class BookRatingCreate(BaseModel):
    rating: int = Field(ge=1, le=5)


class BookReviewSchema(BaseModel):
    id: int
    user_id: str
    rating: int
    is_spoiler: bool = True
    text: str | None = None

    user: UserBookReviewSchema
    book: BookBookReviewSchema

    model_config = ConfigDict(from_attributes=True)
