from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.security import require_role
from backend.app.db.dependencies import get_db
from backend.app.models.category import Category
from backend.app.models.product import Product
from backend.app.models.seller import Seller
from backend.app.models.user import User
from backend.app.schemas.product import (
    ProductCreate,
    ProductResponse,
    ProductStatusUpdate,
    ProductUpdate,
)

router = APIRouter(prefix="/products", tags=["Products"])


@router.get("", response_model=list[ProductResponse])
def list_products(db: Session = Depends(get_db)):
    products = (
        db.query(Product)
        .join(Category, Product.category_id == Category.id)
        .filter(
            Product.is_active.is_(True),
            Category.is_active.is_(True),
        )
        .order_by(Product.created_at.desc())
        .all()
    )
    return products


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: UUID, db: Session = Depends(get_db)):
    product = (
        db.query(Product)
        .join(Category, Product.category_id == Category.id)
        .filter(
            Product.id == product_id,
            Product.is_active.is_(True),
            Category.is_active.is_(True),
        )
        .first()
    )

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    return product


@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_product(
    product_data: ProductCreate,
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

    existing_product = (
        db.query(Product)
        .filter(Product.slug == product_data.slug)
        .first()
    )

    if existing_product:
        raise HTTPException(
            status_code=409,
            detail="Product slug already exists",
        )

    product = Product(
        seller_id=seller.id,
        category_id=product_data.category_id,
        name=product_data.name,
        slug=product_data.slug,
        description=product_data.description,
        base_price=product_data.base_price,
    )

    db.add(product)
    db.commit()
    db.refresh(product)

    return product


@router.put("/{product_id}/details", response_model=ProductResponse)
def update_product(
    product_id: UUID,
    product_data: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("seller")),
):
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

    if product.seller_id != seller.id:
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to modify this product",
        )

    if product_data.slug is not None:
        existing_product = (
            db.query(Product)
            .filter(
                Product.slug == product_data.slug,
                Product.id != product.id,
            )
            .first()
        )

        if existing_product:
            raise HTTPException(
                status_code=409,
                detail="Product slug already exists",
            )

    if product_data.category_id is not None:
        category = (
            db.query(Category)
            .filter(Category.id == product_data.category_id)
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

    update_data = product_data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(product, field, value)

    db.commit()
    db.refresh(product)

    return product


@router.patch("/{product_id}", response_model=ProductResponse)
def update_product_status(
    product_id: UUID,
    product_data: ProductStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("seller")),
):
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

    if product.seller_id != seller.id:
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to modify this product",
        )

    product.is_active = product_data.is_active

    db.commit()
    db.refresh(product)

    return product