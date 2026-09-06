from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.core.security import require_role
from backend.app.db.dependencies import get_db
from backend.app.models.category import Category
from backend.app.models.inventory import Inventory
from backend.app.models.product import Product
from backend.app.models.product_variant import ProductVariant
from backend.app.models.seller import Seller
from backend.app.models.user import User
from backend.app.schemas.inventory import (
    InventoryResponse,
    InventoryStatusUpdate,
    InventoryUpdate,
)

router = APIRouter(
    prefix="/inventory",
    tags=["Inventory"],
)


@router.get(
    "/variants/{variant_id}",
    response_model=InventoryResponse,
)
def get_variant_inventory(
    variant_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("seller")),
):
    seller = (
        db.query(Seller)
        .filter(Seller.user_id == current_user.id)
        .first()
    )

    if seller is None:
        raise HTTPException(
            status_code=403,
            detail="User does not have a seller account",
        )

    inventory = (
        db.query(Inventory)
        .join(
            ProductVariant,
            Inventory.variant_id == ProductVariant.id,
        )
        .join(
            Product,
            ProductVariant.product_id == Product.id,
        )
        .filter(
            Inventory.variant_id == variant_id,
            Product.seller_id == seller.id,
        )
        .first()
    )

    if inventory is None:
        raise HTTPException(
            status_code=404,
            detail="Inventory not found",
        )

    return inventory


@router.put(
    "/variants/{variant_id}",
    response_model=InventoryResponse,
)
def update_variant_inventory(
    variant_id: UUID,
    inventory_data: InventoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("seller")),
):
    seller = (
        db.query(Seller)
        .filter(Seller.user_id == current_user.id)
        .first()
    )

    if seller is None:
        raise HTTPException(
            status_code=403,
            detail="User does not have a seller account",
        )

    variant = (
        db.query(ProductVariant)
        .join(Product, ProductVariant.product_id == Product.id)
        .filter(
            ProductVariant.id == variant_id,
            Product.seller_id == seller.id,
        )
        .first()
    )

    if variant is None:
        raise HTTPException(
            status_code=404,
            detail="Product variant not found",
        )

    product = (
        db.query(Product)
        .filter(Product.id == variant.product_id)
        .first()
    )

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    if not product.is_active:
        raise HTTPException(
            status_code=400,
            detail="Product is not active",
        )

    category = (
        db.query(Category)
        .filter(Category.id == product.category_id)
        .first()
    )

    if category is None:
        raise HTTPException(
            status_code=404,
            detail="Category not found",
        )

    if not category.is_active:
        raise HTTPException(
            status_code=400,
            detail="Category is not active",
        )

    inventory = (
        db.query(Inventory)
        .filter(Inventory.variant_id == variant.id)
        .first()
    )

    if inventory is None:
        inventory = Inventory(
            variant_id=variant.id,
            quantity=inventory_data.quantity,
            reserved_quantity=0,
            reorder_level=inventory_data.reorder_level,
        )
        db.add(inventory)
    else:
        if inventory_data.quantity < inventory.reserved_quantity:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Quantity cannot be lower than the "
                    "currently reserved quantity"
                ),
            )

        inventory.quantity = inventory_data.quantity
        inventory.reorder_level = inventory_data.reorder_level

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Inventory already exists for this product variant",
        )

    db.refresh(inventory)

    return inventory


@router.patch(
    "/variants/{variant_id}",
    response_model=InventoryResponse,
)
def update_inventory_status(
    variant_id: UUID,
    inventory_data: InventoryStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("seller")),
):
    seller = (
        db.query(Seller)
        .filter(Seller.user_id == current_user.id)
        .first()
    )

    if seller is None:
        raise HTTPException(
            status_code=403,
            detail="User does not have a seller account",
        )

    inventory = (
        db.query(Inventory)
        .join(
            ProductVariant,
            Inventory.variant_id == ProductVariant.id,
        )
        .join(
            Product,
            ProductVariant.product_id == Product.id,
        )
        .filter(
            Inventory.variant_id == variant_id,
            Product.seller_id == seller.id,
        )
        .first()
    )

    if inventory is None:
        raise HTTPException(
            status_code=404,
            detail="Inventory not found",
        )

    inventory.is_active = inventory_data.is_active

    db.commit()
    db.refresh(inventory)

    return inventory