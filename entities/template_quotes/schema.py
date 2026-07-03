from datetime import date

from pydantic import BaseModel, ConfigDict


class TemplateQuotesBase(BaseModel):
    quote: str
    author: str
    last_shown_at: date | None = None


class TemplateQuoteCreate(TemplateQuotesBase): ...


class TemplateQuoteUpdate(TemplateQuoteCreate): ...


class TemplateQuoteUpdatePartial(TemplateQuoteUpdate):
    quote: str | None = None
    author: str | None = None


class TemplateQuoteSchema(TemplateQuotesBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
