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
from backend.app.schemas.product_variant import (
    ProductVariantCreate,
    ProductVariantResponse,
    ProductVariantUpdate,
    ProductVariantStatusUpdate,
)

router = APIRouter(prefix="/products", tags=["Product Variants"])


@router.post(
    "/{product_id}/variants",
    response_model=ProductVariantResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_variant(
    product_id: UUID,
    variant_data: ProductVariantCreate,
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

    product = (
        db.query(Product)
        .join(Category, Product.category_id == Category.id)
        .filter(
            Product.id == product_id,
        )
        .first()
    )

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    if product.seller_id != seller.id:
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to modify this product",
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

    existing_variant = (
        db.query(ProductVariant)
        .filter(ProductVariant.sku == variant_data.sku)
        .first()
    )

    if existing_variant:
        raise HTTPException(
            status_code=409,
            detail="Product variant SKU already exists",
        )

    variant = ProductVariant(
        product_id=product.id,
        sku=variant_data.sku,
        price=variant_data.price,
        attributes=variant_data.attributes,
    )

    db.add(variant)
    db.flush()

    inventory = Inventory(
        variant_id=variant.id,
        quantity=0,
        reserved_quantity=0,
        reorder_level=5,
    )

    db.add(inventory)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Product variant SKU already exists",
        )

    db.refresh(variant)

    return variant

@router.put(
    "/{product_id}/variants/{variant_id}/details",
    response_model=ProductVariantResponse,
)
def update_variant_details(
    product_id: UUID,
    variant_id: UUID,
    variant_data: ProductVariantUpdate,
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

    product = (
        db.query(Product)
        .filter(Product.id == product_id)
        .first()
    )

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    if product.seller_id != seller.id:
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to modify this product",
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

    variant = (
        db.query(ProductVariant)
        .filter(
            ProductVariant.id == variant_id,
            ProductVariant.product_id == product_id,
        )
        .first()
    )

    if variant is None:
        raise HTTPException(
            status_code=404,
            detail="Product variant not found",
        )

    update_data = variant_data.model_dump(exclude_unset=True)

    if "sku" in update_data:
        existing_variant = (
            db.query(ProductVariant)
            .filter(
                ProductVariant.sku == update_data["sku"],
                ProductVariant.id != variant.id,
            )
            .first()
        )

        if existing_variant:
            raise HTTPException(
                status_code=409,
                detail="Product variant SKU already exists",
            )

    for field, value in update_data.items():
        setattr(variant, field, value)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Product variant SKU already exists",
        )

    db.refresh(variant)

    return variant

@router.patch(
    "/{product_id}/variants/{variant_id}",
    response_model=ProductVariantResponse,
)
def update_variant_status(
    product_id: UUID,
    variant_id: UUID,
    variant_data: ProductVariantStatusUpdate,
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

    product = (
        db.query(Product)
        .filter(Product.id == product_id)
        .first()
    )

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    if product.seller_id != seller.id:
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to modify this product",
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

    variant = (
        db.query(ProductVariant)
        .filter(
            ProductVariant.id == variant_id,
            ProductVariant.product_id == product_id,
        )
        .first()
    )

    if variant is None:
        raise HTTPException(
            status_code=404,
            detail="Product variant not found",
        )

    variant.is_active = variant_data.is_active

    db.commit()
    db.refresh(variant)

    return variant