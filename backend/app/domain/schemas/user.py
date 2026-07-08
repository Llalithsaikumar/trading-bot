"""User request / response schemas."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import EmailStr, Field

from app.domain.schemas.common import BaseSchema, TimestampSchema

import uuid
from app.domain.enums.user import UserRole, UserStatus


class UserCreate(BaseSchema):
    email: EmailStr
    username: str = Field(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$")
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = None


class UserUpdate(BaseSchema):
    full_name: str | None = None
    username: str | None = Field(default=None, min_length=3, max_length=50)


class PasswordChange(BaseSchema):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class UserResponse(TimestampSchema):
    id: uuid.UUID
    email: str
    username: str
    full_name: str | None
    role: UserRole
    status: UserStatus
    is_active: bool
    is_email_verified: bool
    two_fa_enabled: bool


class UserListItem(BaseSchema):
    id: uuid.UUID
    email: str
    username: str
    role: UserRole
    status: UserStatus
    is_active: bool
