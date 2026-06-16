from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from core.models.users import UserRole, RegisterWays
from utils.custom_validators.nanoid_string_validator import NanoIDString


class UserBase(BaseModel):
    username: str
    email: EmailStr
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


class GoogleSignupRequest(BaseModel):
    username: str
    email: EmailStr


class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp: str


class LoginSchema(BaseModel):
    email: EmailStr
    password: str
