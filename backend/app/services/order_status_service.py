from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.app.models.order import Order, OrderStatus


ALLOWED_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PENDING: {
        OrderStatus.CANCELLED,
    },
    OrderStatus.PAID: {
        OrderStatus.SHIPPED,
        OrderStatus.CANCELLED,
    },
    OrderStatus.SHIPPED: {
        OrderStatus.DELIVERED,
    },
    OrderStatus.DELIVERED: set(),
    OrderStatus.CANCELLED: set(),
}


def transition_order_status(
    db: Session,
    order: Order,
    new_status: OrderStatus,
) -> Order:
    current_status = order.status

    if current_status == new_status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Order is already {current_status.value}",
        )

    allowed_statuses = ALLOWED_TRANSITIONS.get(current_status, set())

    if new_status not in allowed_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Cannot transition order from "
                f"{current_status.value} to {new_status.value}"
            ),
        )

    order.status = new_status

    db.commit()
    db.refresh(order)

    return order