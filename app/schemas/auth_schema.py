import re
from datetime import datetime
from typing import TypeVar

from pydantic import Field, field_validator

from app.core.base_model import AppBaseModel as BaseModel

T = TypeVar("T")


class LoginRequest(BaseModel):
    email: str = Field(max_length=255, example="example@example.com")
    password: str = Field(example="password123")
    # rememberMe: bool = False

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        if not re.match(r"^[^\@\s]+@[^\@\s]+\.[^\@\s]+$", value):
            raise ValueError("Email should match the pattern example@example.com")
        return value

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("Password should contain at least 8 characters")
        return value


class UserProfile(BaseModel):
    userId: str
    firstName: str
    lastName: str
    email: str
    initials: str
    status: str
    lastLogin: datetime | None = None
    createdAt: datetime | None = None
    # {screen: [actions]}, e.g. {"Memeber-Screen": ["save", "view"]}
    permissions: dict[str, list[str]]


class LoginResponse(BaseModel):
    accessToken: str
    refreshToken: str
    expiresIn: int
    tokenType: str = "Bearer"
    # user: UserProfile


class RefreshRequest(BaseModel):
    refreshToken: str


class RefreshResponse(BaseModel):
    accessToken: str
    refreshToken: str
    expiresIn: int


class LoginChallengeResponse(BaseModel):
    """Returned after password check passes — no tokens yet."""

    loginSessionId: str
    otpRequired: bool = True
    expiresIn: int  # seconds
    nextOtpResendTimeInSeconds: int | None = None  # seconds
    otpVerificationAttemptsRemaining: int | None = (
        None  # remaining OTP verification attempts
    )
    otpResendAttemptsRemaining: int | None = None  # remaining OTP resend attempts


class VerifyOtpRequest(BaseModel):
    loginSessionId: str
    otp: str


class ResendOtpRequest(BaseModel):
    loginSessionId: str
