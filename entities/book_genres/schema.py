from pydantic import BaseModel, ConfigDict

from entities.books.short_schema import BookShortSchema


class BookGenreBase(BaseModel):
    title: str
    slug: str
    description: str | None = None


class BookGenreCreate(BookGenreBase): ...


class BookGenreUpdate(BookGenreCreate): ...


class BookGenreUpdatePartial(BookGenreUpdate):
    title: str | None = None
    slug: str | None = None


class BookGenresWithBookSchema(BookGenreBase):
    id: int

    books: list[BookShortSchema] = []

    model_config = ConfigDict(from_attributes=True)


class BookGenreSchema(BookGenreBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
