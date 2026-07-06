"""Order placement and history endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, Query, status

from app.core.dependencies import PaginationParams, get_current_active_user, get_db
from app.domain.schemas.common import PaginatedResponse
from app.domain.schemas.trading import OrderCreate, OrderResponse
from app.services.trading.order_service import OrderService

if TYPE_CHECKING:
    import uuid

router = APIRouter()


@router.get("", response_model=PaginatedResponse[OrderResponse])
async def list_orders(
    portfolio_id: uuid.UUID | None = Query(default=None),
    pagination: PaginationParams = Depends(),
    current_user=Depends(get_current_active_user),
    db=Depends(get_db),
):
    svc = OrderService(db)
    orders, total = await svc.list_orders(
        user_id=current_user.id,
        portfolio_id=portfolio_id,
        offset=pagination.offset,
        limit=pagination.page_size,
    )
    return PaginatedResponse(
        items=orders,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def place_order(
    payload: OrderCreate,
    current_user=Depends(get_current_active_user),
    db=Depends(get_db),
):
    svc = OrderService(db)
    return await svc.place_order(user_id=current_user.id, payload=payload)


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: uuid.UUID,
    current_user=Depends(get_current_active_user),
    db=Depends(get_db),
):
    svc = OrderService(db)
    return await svc.get_order(user_id=current_user.id, order_id=order_id)


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_order(
    order_id: uuid.UUID,
    current_user=Depends(get_current_active_user),
    db=Depends(get_db),
):
    svc = OrderService(db)
    await svc.cancel_order(user_id=current_user.id, order_id=order_id)
