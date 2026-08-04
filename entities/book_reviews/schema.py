from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class BookReviewBase(BaseModel):
    rating: int
    text: str | None = None

    book_id: int
    user_id: str

    created_at: datetime | None = None


class BookReviewCreate(BaseModel):
    rating: int
    text: str | None = None
    book_id: int
    username: str


class BookReviewUpdate(BookReviewBase): ...


class BookReviewUpdatePartial(BookReviewUpdate):
    rating: int | None = None
    book_id: int | None = None
    user_id: int | None = None


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


class BookReviewSchema(BaseModel):
    id: int
    user_id: str
    rating: int
    text: str | None = None

    user: UserBookReviewSchema
    book: BookBookReviewSchema

    model_config = ConfigDict(from_attributes=True)
