from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.app.models.inventory import Inventory
from backend.app.models.order import Order, OrderStatus
from backend.app.models.order_item import OrderItem


def process_mock_payment(
    db: Session,
    order: Order,
    succeed: bool = True,
) -> Order:
    if order.status != OrderStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending orders can be paid",
        )

    order_items = (
        db.query(OrderItem)
        .filter(OrderItem.order_id == order.id)
        .all()
    )

    if not order_items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order has no items",
        )

    if not succeed:
        for item in order_items:
            if item.variant_id is None:
                continue

            inventory = (
                db.query(Inventory)
                .filter(Inventory.variant_id == item.variant_id)
                .with_for_update()
                .first()
            )

            if inventory is not None:
                inventory.reserved_quantity = max(
                    0,
                    inventory.reserved_quantity - item.quantity,
                )

        order.status = OrderStatus.CANCELLED

        db.commit()
        db.refresh(order)

        return order

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
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Inventory not found for SKU {item.sku}",
            )

        if inventory.reserved_quantity < item.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient reserved stock for SKU {item.sku}",
            )

        inventory.reserved_quantity -= item.quantity
        inventory.quantity -= item.quantity

    order.status = OrderStatus.PAID

    db.commit()
    db.refresh(order)

    return order