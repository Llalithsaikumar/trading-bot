"""User management endpoints (authenticated)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    Pagination,
    PaginationParams,
    get_current_active_user,
    get_current_admin_user,
    get_db,
)
from app.domain.schemas.common import PaginatedResponse
from app.domain.schemas.user import PasswordChange, UserListItem, UserResponse, UserUpdate
from app.services.users.user_service import UserService

router = APIRouter()


def _user_service(session: AsyncSession = Depends(get_db)) -> UserService:
    return UserService(session=session)


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user=Depends(get_current_active_user),
) -> UserResponse:
    """Return the authenticated user's profile."""
    return UserResponse.model_validate(current_user)


@router.patch("/me", response_model=UserResponse)
async def update_current_user(
    payload: UserUpdate,
    current_user=Depends(get_current_active_user),
    svc: UserService = Depends(_user_service),
) -> UserResponse:
    """Update profile fields for the authenticated user."""
    return await svc.update_profile(current_user.id, payload)


@router.post("/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    payload: PasswordChange,
    current_user=Depends(get_current_active_user),
    svc: UserService = Depends(_user_service),
) -> None:
    """Change password for the authenticated user."""
    await svc.change_password(current_user, payload)


@router.get("", response_model=PaginatedResponse[UserListItem])
async def list_users(
    pagination: Pagination,
    current_user=Depends(get_current_admin_user),
    svc: UserService = Depends(_user_service),
) -> PaginatedResponse[UserListItem]:
    """List all users (admin only)."""
    return await svc.list_users(
        offset=pagination.offset,
        limit=pagination.page_size,
        page=pagination.page,
    )
