from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

from core.models.challenge import ChallengeType
from entities.books.schema import BookSchema
from utils.custom_validators.nanoid_string_validator import NanoIDString


class UserShortSchema(BaseModel):
    id: NanoIDString
    username: str
    avatar: Optional[str] = None
    avatar_color: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ChallengeBookSchema(BaseModel):
    id: int
    challenge_id: int
    book_id: int
    book: BookSchema

    model_config = ConfigDict(from_attributes=True)


class UserChallengeSchema(BaseModel):
    id: int
    challenge_id: int
    joined_at: datetime
    is_completed: bool = False
    completed_at: Optional[datetime] = None

    user: UserShortSchema

    model_config = ConfigDict(from_attributes=True)


class ChallengeBase(BaseModel):
    title: str
    description: Optional[str] = None
    slug: str
    target_count: int = 1
    challenge_type: ChallengeType = ChallengeType.BOOK
    start_date: date
    end_date: date
    badge_color: Optional[str] = "#3B82F6"
    sponsor_name: Optional[str] = None
    publisher_id: Optional[int] = None


class ChallengeCreate(ChallengeBase): ...


class ChallengeUpdate(ChallengeCreate): ...


class ChallengeUpdatePartial(ChallengeUpdate):
    title: Optional[str] = None
    slug: Optional[str] = None
    target_count: Optional[int] = None
    challenge_type: Optional[ChallengeType] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class ChallengeSchema(ChallengeBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChallengeWithDetailsSchema(ChallengeSchema):
    challenge_books: list[ChallengeBookSchema] = []
    participants: list[UserChallengeSchema] = []

    model_config = ConfigDict(from_attributes=True)
