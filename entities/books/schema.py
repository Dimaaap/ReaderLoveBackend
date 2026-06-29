from pydantic import BaseModel, ConfigDict

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
