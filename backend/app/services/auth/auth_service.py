"""
AuthService — registration, authentication, token lifecycle.
"""
from __future__ import annotations

import uuid

from jose import JWTError
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    AlreadyExistsError,
    AuthenticationError,
    NotFoundError,
    TokenExpiredError,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.domain.enums.user import UserRole, UserStatus
from app.domain.models.user import User
from app.domain.schemas.auth import LoginRequest, LoginResponse, TokenResponse
from app.domain.schemas.user import UserCreate, UserResponse
from app.infrastructure.repositories.user_repository import UserRepository

_REFRESH_BLACKLIST_PREFIX = "blacklist:refresh:"
_REFRESH_TTL = settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 86_400


class AuthService:
    def __init__(self, session: AsyncSession, redis: Redis) -> None:
        self._repo = UserRepository(session)
        self._redis = redis

    async def register(self, payload: UserCreate) -> UserResponse:
        if await self._repo.get_by_email(payload.email):
            raise AlreadyExistsError("Email already registered", code="EMAIL_TAKEN")
        if await self._repo.get_by_username(payload.username):
            raise AlreadyExistsError("Username already taken", code="USERNAME_TAKEN")

        user = User(
            id=uuid.uuid4(),
            email=payload.email,
            username=payload.username,
            hashed_password=hash_password(payload.password),
            full_name=payload.full_name,
            role=UserRole.TRADER,
            status=UserStatus.ACTIVE,
            is_active=True,
            is_email_verified=False,
        )
        user = await self._repo.create(user)
        return UserResponse.model_validate(user)

    async def login(self, payload: LoginRequest) -> LoginResponse:
        user = await self._repo.get_by_email(payload.email)
        if user is None or not verify_password(payload.password, user.hashed_password):
            raise AuthenticationError("Invalid email or password", code="INVALID_CREDENTIALS")

        if not user.is_active:
            raise AuthenticationError("Account is inactive", code="ACCOUNT_INACTIVE")
        if user.status == UserStatus.SUSPENDED:
            raise AuthenticationError("Account suspended", code="ACCOUNT_SUSPENDED")

        tokens = self._issue_tokens(str(user.id))
        return LoginResponse(tokens=tokens, user=UserResponse.model_validate(user))

    async def refresh(self, refresh_token: str) -> TokenResponse:
        try:
            payload = decode_token(refresh_token)
        except JWTError:
            raise TokenExpiredError("Invalid or expired refresh token", code="TOKEN_INVALID")

        if payload.get("type") != "refresh":
            raise AuthenticationError("Not a refresh token", code="TOKEN_TYPE_INVALID")

        blacklist_key = f"{_REFRESH_BLACKLIST_PREFIX}{refresh_token}"
        if await self._redis.exists(blacklist_key):
            raise AuthenticationError("Token has been revoked", code="TOKEN_REVOKED")

        user_id: str | None = payload.get("sub")
        if not user_id:
            raise AuthenticationError("Malformed token", code="TOKEN_MALFORMED")

        user = await self._repo.get_by_id(uuid.UUID(user_id))
        if user is None:
            raise NotFoundError("User not found", code="USER_NOT_FOUND")

        # Rotate: blacklist old, issue new
        await self._redis.setex(blacklist_key, _REFRESH_TTL, "1")
        return self._issue_tokens(user_id)

    async def logout(self, refresh_token: str) -> None:
        blacklist_key = f"{_REFRESH_BLACKLIST_PREFIX}{refresh_token}"
        await self._redis.setex(blacklist_key, _REFRESH_TTL, "1")

    def _issue_tokens(self, user_id: str) -> TokenResponse:
        access = create_access_token(user_id)
        refresh = create_refresh_token(user_id)
        return TokenResponse(
            access_token=access,
            refresh_token=refresh,
            token_type="bearer",
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )
