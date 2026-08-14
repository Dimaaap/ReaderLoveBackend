from pydantic import BaseModel, ConfigDict


class BookPublisherBase(BaseModel):
    title: str
    slug: str


class BookPublisherCreate(BookPublisherBase): ...


class BookPublisherUpdate(BookPublisherCreate): ...


class BookPublisherUpdatePublisher(BookPublisherUpdate):
    title: str | None = None
    slug: str | None = None


class BookPublisherSchema(BookPublisherBase):
    id: int
    title: str
    slug: str

    model_config = ConfigDict(from_attributes=True)
