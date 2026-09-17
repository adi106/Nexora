import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.core.security import require_role
from backend.app.db.dependencies import get_db
from backend.app.models.category import Category
from backend.app.models.order import Order, OrderStatus
from backend.app.models.order_item import OrderItem
from backend.app.models.product import Product
from backend.app.models.seller import Seller
from backend.app.models.user import User
from backend.app.schemas.admin import (
    AdminStatsResponse,
    SellerListResponse,
    UserListResponse,
    UserStatusUpdate,
)
from backend.app.schemas.category import CategoryResponse
from backend.app.schemas.order import OrderResponse
from backend.app.schemas.product import ProductListResponse, ProductStatusUpdate, ProductResponse
from backend.app.schemas.seller import SellerResponse
from backend.app.schemas.user import UserResponse
from backend.app.services.role_service import get_role_names

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/stats", response_model=AdminStatsResponse)
def get_platform_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    user_count = db.query(func.count(User.id)).scalar() or 0
    seller_count = db.query(func.count(Seller.id)).scalar() or 0
    product_count = db.query(func.count(Product.id)).scalar() or 0

    fulfilled_statuses = [OrderStatus.PAID, OrderStatus.SHIPPED, OrderStatus.DELIVERED]

    order_count = (
        db.query(func.count(Order.id)).filter(Order.status.in_(fulfilled_statuses)).scalar() or 0
    )
    total_revenue = (
        db.query(func.coalesce(func.sum(OrderItem.subtotal), 0))
        .join(Order, OrderItem.order_id == Order.id)
        .filter(Order.status.in_(fulfilled_statuses))
        .scalar()
        or 0
    )

    return AdminStatsResponse(
        user_count=user_count,
        seller_count=seller_count,
        product_count=product_count,
        order_count=order_count,
        total_revenue=total_revenue,
    )


@router.get("/users", response_model=UserListResponse)
def list_users(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    query = db.query(User).order_by(User.created_at.desc())

    if search:
        query = query.filter(User.email.ilike(f"%{search}%"))

    total = query.count()
    users = query.offset((page - 1) * page_size).limit(page_size).all()

    items = []
    for user in users:
        response = _user_to_response(user, get_role_names(db, user.id))
        items.append(response)

    return UserListResponse(items=items, total=total, page=page, page_size=page_size)


def _user_to_response(user: User, roles: list[str]) -> UserResponse:
    response = UserResponse.model_validate(user)
    response.roles = roles
    return response


@router.patch("/users/{user_id}/status", response_model=UserResponse)
def set_user_status(
    user_id: uuid.UUID,
    status_data: UserStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot change your own account status")

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = status_data.is_active
    db.commit()
    db.refresh(user)

    return _user_to_response(user, get_role_names(db, user.id))


@router.get("/sellers", response_model=SellerListResponse)
def list_sellers(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    query = db.query(Seller).order_by(Seller.created_at.desc())
    total = query.count()
    sellers = query.offset((page - 1) * page_size).limit(page_size).all()

    return SellerListResponse(items=sellers, total=total, page=page, page_size=page_size)


@router.patch("/sellers/{seller_id}/status", response_model=SellerResponse)
def set_seller_status(
    seller_id: int,
    status_data: UserStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    seller = db.query(Seller).filter(Seller.id == seller_id).first()
    if seller is None:
        raise HTTPException(status_code=404, detail="Seller not found")

    seller.is_active = status_data.is_active
    db.commit()
    db.refresh(seller)

    return seller


@router.get("/products", response_model=ProductListResponse)
def list_all_products(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    seller_id: int | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    query = db.query(Product).order_by(Product.created_at.desc())

    if seller_id is not None:
        query = query.filter(Product.seller_id == seller_id)

    if is_active is not None:
        query = query.filter(Product.is_active.is_(is_active))

    total = query.count()
    products = query.offset((page - 1) * page_size).limit(page_size).all()

    return ProductListResponse(items=products, total=total, page=page, page_size=page_size)


@router.patch("/products/{product_id}/status", response_model=ProductResponse)
def set_any_product_status(
    product_id: uuid.UUID,
    status_data: ProductStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    product.is_active = status_data.is_active
    db.commit()
    db.refresh(product)

    return product


@router.get("/categories", response_model=list[CategoryResponse])
def list_all_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    return db.query(Category).order_by(Category.name.asc()).all()


@router.get("/orders", response_model=list[OrderResponse])
def list_all_orders(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    return (
        db.query(Order)
        .order_by(Order.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
