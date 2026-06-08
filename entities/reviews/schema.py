from pydantic import BaseModel, ConfigDict


class ReviewBase(BaseModel):
    review_text: str
    user_name: str
    title: str


class ReviewCreate(ReviewBase): ...


class ReviewUpdate(ReviewCreate): ...


class ReviewUpdatePartial(ReviewUpdate):
    review_text: str | None = None
    user_name: str | None = None
    title: str | None = None


class ReviewSchema(ReviewBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
