"""Authentication endpoints: register, login, refresh, logout."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, status

from app.core.dependencies import get_db, get_redis
from app.domain.schemas.auth import LoginRequest, LoginResponse, RefreshRequest, TokenResponse
from app.domain.schemas.user import UserCreate, UserResponse
from app.services.auth.auth_service import AuthService

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


def _auth_service(
    session: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> AuthService:
    return AuthService(session=session, redis=redis)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: UserCreate,
    svc: AuthService = Depends(_auth_service),
) -> UserResponse:
    """Create a new user account."""
    return await svc.register(payload)


@router.post("/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest,
    svc: AuthService = Depends(_auth_service),
) -> LoginResponse:
    """Authenticate and receive access + refresh tokens."""
    return await svc.login(payload)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    payload: RefreshRequest,
    svc: AuthService = Depends(_auth_service),
) -> TokenResponse:
    """Exchange a valid refresh token for a new access token."""
    return await svc.refresh(payload.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    payload: RefreshRequest,
    svc: AuthService = Depends(_auth_service),
) -> None:
    """Invalidate the session by blacklisting the refresh token."""
    await svc.logout(payload.refresh_token)
