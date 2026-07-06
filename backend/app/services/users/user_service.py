"""
UserService — profile management and admin user listing.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AlreadyExistsError, AuthenticationError, NotFoundError
from app.core.security import hash_password, verify_password
from app.domain.models.user import User
from app.domain.schemas.common import PaginatedResponse
from app.domain.schemas.user import (
    PasswordChange,
    UserListItem,
    UserResponse,
    UserUpdate,
)
from app.infrastructure.repositories.user_repository import UserRepository


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = UserRepository(session)

    async def get_profile(self, user_id: uuid.UUID) -> UserResponse:
        user = await self._repo.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User not found", code="USER_NOT_FOUND")
        return UserResponse.model_validate(user)

    async def update_profile(self, user_id: uuid.UUID, payload: UserUpdate) -> UserResponse:
        update_data: dict = payload.model_dump(exclude_none=True)

        if "username" in update_data:
            existing = await self._repo.get_by_username(update_data["username"])
            if existing and existing.id != user_id:
                raise AlreadyExistsError("Username already taken", code="USERNAME_TAKEN")

        user = await self._repo.update(user_id, update_data)
        if user is None:
            raise NotFoundError("User not found", code="USER_NOT_FOUND")
        return UserResponse.model_validate(user)

    async def change_password(self, user: User, payload: PasswordChange) -> None:
        if not verify_password(payload.current_password, user.hashed_password):
            raise AuthenticationError("Current password is incorrect", code="WRONG_PASSWORD")
        await self._repo.update(user.id, {"hashed_password": hash_password(payload.new_password)})

    async def list_users(
        self, offset: int = 0, limit: int = 20, page: int = 1
    ) -> PaginatedResponse[UserListItem]:
        users, total = await self._repo.get_all(offset=offset, limit=limit)
        items = [UserListItem.model_validate(u) for u in users]
        return PaginatedResponse.from_list(items, total=total, page=page, page_size=limit)
