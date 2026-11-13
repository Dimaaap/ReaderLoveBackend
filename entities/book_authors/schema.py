from pydantic import BaseModel, ConfigDict


class CountryShortSchema(BaseModel):
    id: int
    name: str
    name_uk: str
    code: str
    flag: str | None = None

    model_config = ConfigDict(from_attributes=True)


class BookAuthorsBase(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    slug: str


class BookAuthorsCreate(BookAuthorsBase):
    country_id: int | None = None


class BookAuthorsUpdate(BookAuthorsCreate): ...


class BookAuthorsUpdatePartial(BookAuthorsUpdate):
    first_name: str | None = None
    last_name: str | None = None
    slug: str | None = None
    country_id: int | None = None


class BookAuthorsSchema(BookAuthorsBase):
    id: int
    country_id: int | None = None
    country: CountryShortSchema | None = None

    model_config = ConfigDict(from_attributes=True)
