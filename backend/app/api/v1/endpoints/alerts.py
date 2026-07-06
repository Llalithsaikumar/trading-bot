"""Price alert CRUD endpoints (not yet implemented)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import Pagination, get_current_active_user
from app.domain.schemas.common import PaginatedResponse

if TYPE_CHECKING:
    import uuid

router = APIRouter()

_NOT_IMPLEMENTED = HTTPException(
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
    detail="Alerts not yet implemented",
)


@router.get("", response_model=PaginatedResponse[dict])
async def list_alerts(
    pagination: Pagination,
    current_user=Depends(get_current_active_user),
):
    raise _NOT_IMPLEMENTED


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_alert(current_user=Depends(get_current_active_user)):
    raise _NOT_IMPLEMENTED


@router.delete("/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert(
    alert_id: uuid.UUID,
    current_user=Depends(get_current_active_user),
):
    raise _NOT_IMPLEMENTED
