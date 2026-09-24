from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

from core.models.user_book_association import BookReadStatus
from entities.books.schema import BookSchema


class BookWithUserStatusSchema(BookSchema):
    user_read_status: Optional[BookReadStatus] = None


class BookSelectionItemSchema(BaseModel):
    book_id: int
    book: BookWithUserStatusSchema

    model_config = ConfigDict(from_attributes=True)


class BookSelectionBase(BaseModel):
    title: str
    slug: str
    description: Optional[str] = Field(
        None, description="Description for the book selection"
    )
    author_name: str = "Редакція ExLove"
    cover_image: Optional[str] = None
    is_active: bool = True


class BookSelectionCreate(BookSelectionBase):
    book_ids: list[int] = []


class BookSelectionUpdate(BookSelectionBase): ...


class BookSelectionUpdatePartial(BookSelectionUpdate):
    title: Optional[str] = None
    slug: Optional[str] = None
    author_name: Optional[str] = None
    is_active: Optional[bool] = None


class BookSelectionSchema(BookSelectionBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class BookSelectionSummarySchema(BookSelectionBase):
    books_count: int = 0


class BookSelectionWithDetailsSchema(BookSelectionBase):
    books: list[BookWithUserStatusSchema] = []

    model_config = ConfigDict(from_attributes=True)
