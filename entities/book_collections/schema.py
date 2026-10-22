from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

from core.models.user_book_association import BookReadStatus
from entities.books.schema import BookSchema


class BookWithUserStatusSchema(BookSchema):
    user_read_status: Optional[BookReadStatus] = None


class BookCollectionItemScheme(BaseModel):
    book_id: int
    book: BookWithUserStatusSchema

    model_config = ConfigDict(from_attributes=True)


class BookCollectionBase(BaseModel):
    title: str
    description: Optional[str] = Field(
        None, description="Description for the book collection"
    )

    is_public: bool = True


class BookCollectionCreate(BookCollectionBase):
    book_ids: list[int] = []


class BookCollectionUpdate(BookCollectionBase): ...


class BookCollectionUpdatePartial(BookCollectionUpdate):
    title: Optional[str] = None
    description: Optional[str] = None
    is_public: Optional[bool] = None


class BookCollectionSchema(BookCollectionBase):
    id: int
    user_id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class BookCollectionSummarySchema(BookCollectionBase):
    id: int
    user_id: str
    books_count: int = 0
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class BookCollectionWithDetailsSchema(BookCollectionBase):
    id: int
    user_id: str
    books: list[BookWithUserStatusSchema]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
