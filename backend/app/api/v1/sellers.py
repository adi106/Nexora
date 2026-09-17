import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.core.security import get_current_user
from backend.app.db.dependencies import get_db
from backend.app.models.inventory import Inventory
from backend.app.models.order import Order, OrderStatus
from backend.app.models.order_item import OrderItem
from backend.app.models.product import Product
from backend.app.models.product_variant import ProductVariant
from backend.app.models.role import Role
from backend.app.models.seller import Seller
from backend.app.models.user import User
from backend.app.models.user_role import UserRole
from backend.app.schemas.order import OrderResponse
from backend.app.schemas.product import (
    ProductDetailResponse,
    ProductDetailVariantResponse,
    ProductListResponse,
)
from backend.app.schemas.seller import SellerCreate, SellerResponse, SellerStatsResponse

router = APIRouter(prefix="/sellers", tags=["Sellers"])


def _get_own_seller(db: Session, user_id: uuid.UUID) -> Seller:
    seller = db.query(Seller).filter(Seller.user_id == user_id).first()
    if seller is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You do not have a seller account yet",
        )
    return seller


@router.post("", response_model=SellerResponse, status_code=status.HTTP_201_CREATED)
def become_seller(
    seller_data: SellerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = db.query(Seller).filter(Seller.user_id == current_user.id).first()
    if existing is not None:
        raise HTTPException(status_code=409, detail="You already have a seller account")

    seller = Seller(
        user_id=current_user.id,
        store_name=seller_data.store_name,
        store_slug=seller_data.store_slug,
        description=seller_data.description,
    )
    db.add(seller)

    seller_role = db.query(Role).filter(Role.name == "seller").first()
    if seller_role is None:
        raise HTTPException(status_code=500, detail="Seller role is not configured")

    has_role = (
        db.query(UserRole)
        .filter(UserRole.user_id == current_user.id, UserRole.role_id == seller_role.id)
        .first()
    )
    if has_role is None:
        db.add(UserRole(user_id=current_user.id, role_id=seller_role.id))

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Store name or slug already taken")

    db.refresh(seller)
    return seller


@router.get("/me", response_model=SellerResponse)
def get_my_seller_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _get_own_seller(db, current_user.id)


@router.get("/me/stats", response_model=SellerStatsResponse)
def get_my_seller_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    seller = _get_own_seller(db, current_user.id)

    product_count = (
        db.query(func.count(Product.id))
        .filter(Product.seller_id == seller.id)
        .scalar()
        or 0
    )

    fulfilled_statuses = [OrderStatus.PAID, OrderStatus.SHIPPED, OrderStatus.DELIVERED]

    sales_query = (
        db.query(
            func.coalesce(func.sum(OrderItem.subtotal), 0),
            func.count(func.distinct(OrderItem.order_id)),
            func.count(func.distinct(Order.user_id)),
        )
        .join(Order, OrderItem.order_id == Order.id)
        .join(ProductVariant, OrderItem.variant_id == ProductVariant.id)
        .join(Product, ProductVariant.product_id == Product.id)
        .filter(Product.seller_id == seller.id, Order.status.in_(fulfilled_statuses))
        .first()
    )

    total_revenue, order_count, customer_count = sales_query

    return SellerStatsResponse(
        total_revenue=total_revenue,
        order_count=order_count,
        product_count=product_count,
        customer_count=customer_count,
    )


@router.get("/me/products", response_model=ProductListResponse)
def list_my_products(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    seller = _get_own_seller(db, current_user.id)

    query = (
        db.query(Product)
        .filter(Product.seller_id == seller.id)
        .order_by(Product.created_at.desc())
    )

    total = query.count()
    products = query.offset((page - 1) * page_size).limit(page_size).all()

    return ProductListResponse(items=products, total=total, page=page, page_size=page_size)


@router.get("/me/products/{product_id}", response_model=ProductDetailResponse)
def get_my_product(
    product_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    seller = _get_own_seller(db, current_user.id)

    product = (
        db.query(Product)
        .filter(Product.id == product_id, Product.seller_id == seller.id)
        .first()
    )

    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    variants = (
        db.query(ProductVariant, Inventory)
        .outerjoin(Inventory, Inventory.variant_id == ProductVariant.id)
        .filter(ProductVariant.product_id == product.id)
        .all()
    )

    variant_responses = []
    for variant, inventory in variants:
        available_quantity = 0
        if variant.is_active and inventory is not None and inventory.is_active:
            available_quantity = max(inventory.quantity - inventory.reserved_quantity, 0)

        variant_responses.append(
            ProductDetailVariantResponse(
                id=variant.id,
                product_id=variant.product_id,
                sku=variant.sku,
                price=variant.price,
                attributes=variant.attributes,
                is_active=variant.is_active,
                available_quantity=available_quantity,
            )
        )

    return ProductDetailResponse(
        id=product.id,
        seller_id=product.seller_id,
        category_id=product.category_id,
        name=product.name,
        slug=product.slug,
        description=product.description,
        base_price=product.base_price,
        is_active=product.is_active,
        created_at=product.created_at,
        updated_at=product.updated_at,
        variants=variant_responses,
    )


@router.get("/me/orders", response_model=list[OrderResponse])
def list_my_seller_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    seller = _get_own_seller(db, current_user.id)

    order_ids = (
        db.query(Order.id)
        .join(OrderItem, OrderItem.order_id == Order.id)
        .join(ProductVariant, OrderItem.variant_id == ProductVariant.id)
        .join(Product, ProductVariant.product_id == Product.id)
        .filter(Product.seller_id == seller.id)
        .distinct()
        .subquery()
    )

    return (
        db.query(Order)
        .filter(Order.id.in_(db.query(order_ids)))
        .order_by(Order.created_at.desc())
        .all()
    )
