from pydantic import BaseModel, ConfigDict


class BookAuthorsBase(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    slug: str


class BookAuthorsCreate(BookAuthorsBase): ...


class BookAuthorsUpdate(BookAuthorsCreate): ...


class BookAuthorsUpdatePartial(BookAuthorsUpdate):
    slug: str | None = None


class BookAuthorsSchema(BookAuthorsBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
