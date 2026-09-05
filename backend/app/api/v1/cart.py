import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.security import get_current_user
from backend.app.db.dependencies import get_db
from backend.app.models.cart import Cart, CartStatus
from backend.app.models.cart_item import CartItem
from backend.app.models.inventory import Inventory
from backend.app.models.product_variant import ProductVariant
from backend.app.models.user import User
from backend.app.schemas.cart import (
    CartItemCreate,
    CartItemResponse,
    CartItemUpdate,
    CartResponse,
)


router = APIRouter(
    prefix="/cart",
    tags=["Cart"],
)


@router.get(
    "",
    response_model=CartResponse,
)
def get_cart(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cart = (
        db.query(Cart)
        .filter(
            Cart.user_id == current_user.id,
            Cart.status == CartStatus.ACTIVE,
        )
        .first()
    )

    if cart is None:
        cart = Cart(
            user_id=current_user.id,
            status=CartStatus.ACTIVE,
        )

        db.add(cart)
        db.commit()
        db.refresh(cart)

    return cart


@router.post(
    "/items",
    response_model=CartItemResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_cart_item(
    item_data: CartItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cart = (
        db.query(Cart)
        .filter(
            Cart.user_id == current_user.id,
            Cart.status == CartStatus.ACTIVE,
        )
        .first()
    )

    if cart is None:
        cart = Cart(
            user_id=current_user.id,
            status=CartStatus.ACTIVE,
        )

        db.add(cart)
        db.flush()

    variant = (
        db.query(ProductVariant)
        .filter(
            ProductVariant.id == item_data.variant_id,
            ProductVariant.is_active.is_(True),
        )
        .first()
    )

    if variant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product variant not found",
        )

    inventory = (
        db.query(Inventory)
        .filter(
            Inventory.variant_id == variant.id,
            Inventory.is_active.is_(True),
        )
        .first()
    )

    if inventory is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Product is not available",
        )

    available_stock = (
        inventory.quantity - inventory.reserved_quantity
    )

    existing_item = (
        db.query(CartItem)
        .filter(
            CartItem.cart_id == cart.id,
            CartItem.variant_id == item_data.variant_id,
        )
        .first()
    )

    if existing_item:
        new_quantity = existing_item.quantity + item_data.quantity

        if new_quantity > available_stock:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Only {available_stock} items available",
            )

        existing_item.quantity = new_quantity

        db.commit()
        db.refresh(existing_item)

        return existing_item

    if item_data.quantity > available_stock:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only {available_stock} items available",
        )

    cart_item = CartItem(
        cart_id=cart.id,
        variant_id=item_data.variant_id,
        quantity=item_data.quantity,
    )

    db.add(cart_item)
    db.commit()
    db.refresh(cart_item)

    return cart_item


@router.put(
    "/items/{item_id}",
    response_model=CartItemResponse,
)
def update_cart_item(
    item_id: uuid.UUID,
    item_data: CartItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
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
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active cart not found",
        )

    item = (
        db.query(CartItem)
        .filter(
            CartItem.id == item_id,
            CartItem.cart_id == cart.id,
        )
        .first()
    )

    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart item not found",
        )

    variant = (
        db.query(ProductVariant)
        .filter(
            ProductVariant.id == item.variant_id,
            ProductVariant.is_active.is_(True),
        )
        .first()
    )

    if variant is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Product variant is not available",
        )

    inventory = (
        db.query(Inventory)
        .filter(
            Inventory.variant_id == variant.id,
            Inventory.is_active.is_(True),
        )
        .first()
    )

    if inventory is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Product is not available",
        )

    available_stock = (
        inventory.quantity - inventory.reserved_quantity
    )

    if item_data.quantity > available_stock:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only {available_stock} items available",
        )

    item.quantity = item_data.quantity

    db.commit()
    db.refresh(item)

    return item


@router.delete(
    "/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_cart_item(
    item_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
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
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active cart not found",
        )

    item = (
        db.query(CartItem)
        .filter(
            CartItem.id == item_id,
            CartItem.cart_id == cart.id,
        )
        .first()
    )

    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart item not found",
        )

    db.delete(item)
    db.commit()