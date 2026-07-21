from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from core.models.users import UserRole, RegisterWays, AvatarColors
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


class LoginSchema(BaseModel):
    email: EmailStr
    password: str
