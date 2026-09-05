from datetime import datetime, timezone

from sqlalchemy.orm import Session

from backend.app.models.inventory import Inventory
from backend.app.models.order import Order, OrderStatus
from backend.app.models.order_item import OrderItem


def expire_pending_orders(
    db: Session,
    now: datetime | None = None,
) -> int:
    """
    Cancel expired pending orders and release their reserved inventory.

    Returns the number of orders expired.

    The operation is idempotent because only PENDING orders are selected.
    Once an order is cancelled, subsequent executions will ignore it.
    """

    current_time = now or datetime.now(timezone.utc)

    expired_orders = (
        db.query(Order)
        .filter(
            Order.status == OrderStatus.PENDING,
            Order.reservation_expires_at.is_not(None),
            Order.reservation_expires_at <= current_time,
        )
        .with_for_update()
        .all()
    )

    expired_count = 0

    for order in expired_orders:
        order_items = (
            db.query(OrderItem)
            .filter(OrderItem.order_id == order.id)
            .all()
        )

        for item in order_items:
            if item.variant_id is None:
                continue

            inventory = (
                db.query(Inventory)
                .filter(Inventory.variant_id == item.variant_id)
                .with_for_update()
                .first()
            )

            if inventory is None:
                continue

            inventory.reserved_quantity = max(
                0,
                inventory.reserved_quantity - item.quantity,
            )

        order.status = OrderStatus.CANCELLED
        expired_count += 1

    if expired_count:
        db.commit()

    return expired_count