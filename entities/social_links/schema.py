from pydantic import BaseModel, ConfigDict


class SocialLinkBase(BaseModel):
    title: str
    link: str
    background_color: str | None = None
    image_src: str | None = None


class SocialLinkCreate(SocialLinkBase): ...


class SocialLinkUpdate(SocialLinkCreate): ...


class SocialLinkUpdatePartial(SocialLinkUpdate):
    title: str | None = None
    link: str | None = None


class SocialLinkSchema(SocialLinkBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
