from pydantic import BaseModel, ConfigDict


class BookGenreBase(BaseModel):
    title: str
    slug: str
    description: str | None = None


class BookGenreCreate(BookGenreBase): ...


class BookGenreUpdate(BookGenreCreate): ...


class BookGenreUpdatePartial(BookGenreUpdate):
    title: str | None = None
    slug: str | None = None


class BookGenreSchema(BookGenreBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
