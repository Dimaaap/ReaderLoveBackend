from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from core.models.users import UserRole, RegisterWays, AvatarColors
from entities.user_settings.schema import UserSettingsSchema
from utils.custom_validators.nanoid_string_validator import NanoIDString


class UserBase(BaseModel):
    username: str
    email: EmailStr
    avatar: str | None = None
    avatar_color: AvatarColors | None = None
    about_info: str | None = None
    date_joined: datetime | None = None
    role: UserRole = UserRole.USER
    is_verified: bool = False


class CreateUser(UserBase):
    password_hash: str | None = None
    register_way: RegisterWays = RegisterWays.SITE


class UpdateUser(CreateUser): ...


class UpdateUserPartial(UpdateUser):
    username: str | None = None
    email: EmailStr | None = None
    role: UserRole | None = None


class UserSchema(UserBase):
    model_config = ConfigDict(from_attributes=True)

    settings: UserSettingsSchema

    id: NanoIDString


class SignupRequest(BaseModel):
    username: str
    email: EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6)
    new_password: str = Field(..., min_length=6)


class GoogleSignupRequest(BaseModel):
    username: str
    email: EmailStr


class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp: str


class ChangePasswordSchema(BaseModel):
    current_password: str = Field(min_length=6)
    new_password: str = Field(min_length=6)


class UpdateUserSettings(BaseModel):
    email_notifications: bool | None = None
    reading_reminders: bool | None = None
    book_recommendations: bool | None = None
    is_public_profile: bool | None = None
    is_show_reading_progress: bool | None = None
    allow_friends_recommendations: bool | None = None
    show_statistics: bool | None = None
    show_bookshelf: bool | None = None
    show_favorite_books: bool | None = None
    show_notes: bool | None = None
    show_quotes: bool | None = None
    show_goals: bool | None = None
    show_current_book: bool | None = None
    show_followers: bool | None = None
    allow_private_messages: bool | None = None
    show_online_status: bool | None = None
    show_last_seen: bool | None = None


class DeleteAccountSchema(BaseModel):
    password: str


class LoginSchema(BaseModel):
    email: EmailStr
    password: str
