from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, Field
from pydantic.generics import GenericModel

T = TypeVar("T")


class LoginRequest(BaseModel):
    email: str = Field(
        max_length=255,
        pattern=r"^[^\@\s]+@[^\@\s]+\.[^\@\s]+$",
        example="eample@example.com",
    )
    password: str = Field(min_length=8, example="password123")
    # rememberMe: bool = False


class UserProfile(BaseModel):
    userId: str
    firstName: str
    lastName: str
    email: str
    role: str
    initials: str
    status: str
    lastLogin: datetime | None = None
    createdAt: datetime | None = None
    permissions: list[str]


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


class ApiResponse(GenericModel, Generic[T]):
    success: bool
    message: str
    data: T | None = None
    errors: list[str] = []

    @classmethod
    def ok(cls, data: T, message: str = "Success") -> "ApiResponse[T]":
        return cls(success=True, message=message, data=data)

    @classmethod
    def fail(cls, message: str, errors: list[str] | None = None) -> "ApiResponse[None]":
        return cls(success=False, message=message, data=None, errors=errors or [])
