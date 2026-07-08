from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from core.models.book_notes import NoteCategory


class BookNotesBase(BaseModel):
    book_id: int
    user_username: str

    note_text: str
    note_category: NoteCategory
    is_important: bool = False
    book_page: int | None = None

    created_at: datetime | None = None


class BookNotesCreate(BookNotesBase): ...


class BookNotesUpdate(BookNotesCreate): ...


class BookNotesUpdatePartial(BookNotesUpdate):
    book_id: int | None = None

    note_text: str | None = None
    note_category: NoteCategory | None = None
    is_important: bool | None = None

    created_at: datetime | None = None


class UserBookNotesSchema(BaseModel):
    username: str
    email: EmailStr

    model_config = ConfigDict(from_attributes=True)


class BookBookNotesSchema(BaseModel):
    title: str
    slug: str
    image_link: str
    pages_count: int

    model_config = ConfigDict(from_attributes=True)


class BookNotesSchema(BookNotesBase):
    id: int
    user_username: str | None = None

    user: UserBookNotesSchema
    book: BookBookNotesSchema

    model_config = ConfigDict(from_attributes=True)
