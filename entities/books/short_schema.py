from pydantic import BaseModel, ConfigDict

from entities.book_authors.schema import BookAuthorsSchema


class BookShortSchema(BaseModel):
    id: int
    title: str
    slug: str
    image_link: str
    authors: list[BookAuthorsSchema]

    model_config = ConfigDict(from_attributes=True)
