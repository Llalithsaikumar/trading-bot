"""Strategy CRUD + control endpoints (not yet implemented)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import Pagination, get_current_active_user
from app.domain.schemas.common import MessageResponse, PaginatedResponse
from app.domain.schemas.strategy import StrategyCreate, StrategyResponse, StrategyUpdate

router = APIRouter()

_NOT_IMPLEMENTED = HTTPException(
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
    detail="Strategies not yet implemented",
)


@router.get("", response_model=PaginatedResponse[StrategyResponse])
async def list_strategies(
    pagination: Pagination,
    current_user=Depends(get_current_active_user),
):
    raise _NOT_IMPLEMENTED


@router.post("", response_model=StrategyResponse, status_code=status.HTTP_201_CREATED)
async def create_strategy(
    payload: StrategyCreate,
    current_user=Depends(get_current_active_user),
):
    raise _NOT_IMPLEMENTED


@router.get("/{strategy_id}", response_model=StrategyResponse)
async def get_strategy(
    strategy_id: uuid.UUID,
    current_user=Depends(get_current_active_user),
):
    raise _NOT_IMPLEMENTED


@router.patch("/{strategy_id}", response_model=StrategyResponse)
async def update_strategy(
    strategy_id: uuid.UUID,
    payload: StrategyUpdate,
    current_user=Depends(get_current_active_user),
):
    raise _NOT_IMPLEMENTED


@router.delete("/{strategy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_strategy(
    strategy_id: uuid.UUID,
    current_user=Depends(get_current_active_user),
):
    raise _NOT_IMPLEMENTED


@router.post("/{strategy_id}/start", response_model=MessageResponse)
async def start_strategy(
    strategy_id: uuid.UUID,
    current_user=Depends(get_current_active_user),
):
    raise _NOT_IMPLEMENTED


@router.post("/{strategy_id}/stop", response_model=MessageResponse)
async def stop_strategy(
    strategy_id: uuid.UUID,
    current_user=Depends(get_current_active_user),
):
    raise _NOT_IMPLEMENTED
