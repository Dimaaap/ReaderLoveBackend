from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class CountryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    code: str = Field(..., min_length=2, max_length=2)
    flag: Optional[str] = Field(None, max_length=10)


class CountryCreate(CountryBase):
    pass


class CountryUpdate(CountryBase):
    pass


class CountryUpdatePartial(CountryUpdate):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    code: Optional[str] = Field(None, min_length=2, max_length=2)
    flag: Optional[str] = Field(None, max_length=10)


class CountrySchema(CountryBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class CountrySummarySchema(CountryBase):
    id: int
    authors_count: int = 0

    model_config = ConfigDict(from_attributes=True)
