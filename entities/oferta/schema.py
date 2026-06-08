from datetime import datetime

from pydantic import BaseModel, ConfigDict


class OfertaBase(BaseModel):
    html_code: str
    last_update: datetime


class OfertaCreate(OfertaBase): ...


class OfertaUpdate(OfertaCreate): ...


class OfertaUpdatePartial(OfertaUpdate):
    html_code: str | None = None
    last_update: datetime | None = None


class OfertaSchema(OfertaBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
