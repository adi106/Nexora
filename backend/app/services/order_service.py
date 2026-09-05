from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.app.models.address import Address
from backend.app.models.cart import Cart, CartStatus
from backend.app.models.cart_item import CartItem
from backend.app.models.inventory import Inventory
from backend.app.models.order import Order, OrderStatus
from backend.app.models.order_item import OrderItem
from backend.app.models.product_variant import ProductVariant
from backend.app.models.user import User


def create_order_from_cart(
    db: Session,
    current_user: User,
    address_id,
) -> Order:
    address = (
        db.query(Address)
        .filter(
            Address.id == address_id,
            Address.user_id == current_user.id,
        )
        .first()
    )

    if address is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shipping address not found",
        )

    cart = (
        db.query(Cart)
        .filter(
            Cart.user_id == current_user.id,
            Cart.status == CartStatus.ACTIVE,
        )
        .first()
    )

    if cart is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Active cart not found",
        )

    if not cart.items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cart is empty",
        )

    total_amount = Decimal("0.00")
    order_items = []

    for cart_item in cart.items:
        variant = (
            db.query(ProductVariant)
            .filter(
                ProductVariant.id == cart_item.variant_id,
                ProductVariant.is_active.is_(True),
            )
            .first()
        )

        if variant is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A product in your cart is no longer available",
            )

        inventory = (
            db.query(Inventory)
            .filter(
                Inventory.variant_id == variant.id,
                Inventory.is_active.is_(True),
            )
            .with_for_update()
            .first()
        )

        if inventory is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Product {variant.sku} is not available",
            )

        available_stock = (
            inventory.quantity - inventory.reserved_quantity
        )

        if cart_item.quantity > available_stock:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Only {available_stock} items available "
                    f"for {variant.sku}"
                ),
            )

        inventory.reserved_quantity += cart_item.quantity

        unit_price = variant.price
        subtotal = unit_price * cart_item.quantity

        total_amount += subtotal

        order_items.append(
            {
                "variant_id": variant.id,
                "product_name": variant.product.name,
                "sku": variant.sku,
                "unit_price": unit_price,
                "quantity": cart_item.quantity,
                "subtotal": subtotal,
            }
        )

    order = Order(
        user_id=current_user.id,
        status=OrderStatus.PENDING,
        total_amount=total_amount,
        shipping_full_name=(
            f"{current_user.first_name} {current_user.last_name}"
        ).strip(),
        shipping_address_line1=address.address_line1,
        shipping_address_line2=address.address_line2,
        shipping_city=address.city,
        shipping_region=address.region,
        shipping_postal_code=address.postal_code,
        shipping_country_code=address.country_code,
    )

    db.add(order)
    db.flush()

    for item_data in order_items:
        db.add(
            OrderItem(
                order_id=order.id,
                **item_data,
            )
        )

    cart.status = CartStatus.CONVERTED

    db.commit()
    db.refresh(order)

    return order