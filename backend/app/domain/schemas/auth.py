"""Auth request / response schemas."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.domain.schemas.common import BaseSchema

from pydantic import EmailStr
from app.domain.schemas.user import UserResponse


class LoginRequest(BaseSchema):
    email: EmailStr
    password: str


class TokenResponse(BaseSchema):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class RefreshRequest(BaseSchema):
    refresh_token: str


class LoginResponse(BaseSchema):
    tokens: TokenResponse
    user: UserResponse
