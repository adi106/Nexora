from uuid import UUID
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.core.security import require_role
from backend.app.db.dependencies import get_db
from backend.app.models.category import Category
from backend.app.models.inventory import Inventory
from backend.app.models.product_variant import ProductVariant
from backend.app.models.product import Product
from backend.app.models.seller import Seller
from backend.app.models.user import User
from backend.app.schemas.product import (
    ProductCreate,
    ProductDetailResponse,
    ProductListResponse,
    ProductResponse,
    ProductStatusUpdate,
    ProductUpdate,
    ProductDetailVariantResponse,
)

router = APIRouter(prefix="/products", tags=["Products"])


@router.get("", response_model=ProductListResponse)
def list_products(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    sort: str = Query(default="newest"),
    category_id: int | None = Query(default=None, ge=1),
    seller_id: int | None = Query(default=None, ge=1),
    min_price: Decimal | None = Query(default=None, gt=0),
    max_price: Decimal | None = Query(default=None, gt=0),
    in_stock: bool | None = Query(default=None),
    search: str | None = Query(default=None, min_length=1),
    db: Session = Depends(get_db),
):
    query = (
        db.query(Product)
        .join(Category, Product.category_id == Category.id)
        .filter(
            Product.is_active.is_(True),
            Category.is_active.is_(True),
        )
    )

    if category_id is not None:
        query = query.filter(Product.category_id == category_id)

    if seller_id is not None:
        query = query.filter(Product.seller_id == seller_id)

    if min_price is not None:
        query = query.filter(Product.base_price >= min_price)

    if max_price is not None:
        query = query.filter(Product.base_price <= max_price)

    if search is not None:
        search_term = f"%{search.strip()}%"
        query = query.filter(
            Product.name.ilike(search_term)
            | Product.description.ilike(search_term)
        )

    if in_stock is True:
        query = query.filter(
            db.query(ProductVariant.id)
            .join(
                Inventory,
                Inventory.variant_id == ProductVariant.id,
            )
            .filter(
                ProductVariant.product_id == Product.id,
                ProductVariant.is_active.is_(True),
                Inventory.is_active.is_(True),
                (Inventory.quantity - Inventory.reserved_quantity) > 0,
            )
            .exists()
    )

    total = query.count()

    if sort == "price_asc":
        query = query.order_by(Product.base_price.asc())
    elif sort == "price_desc":
        query = query.order_by(Product.base_price.desc())
    elif sort == "newest":
        query = query.order_by(Product.created_at.desc())
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid sort option",
        )

    products = (
        query
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return ProductListResponse(
        items=products,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{product_id}", response_model=ProductDetailResponse)
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

    variants = (
        db.query(ProductVariant, Inventory)
        .outerjoin(
            Inventory,
            Inventory.variant_id == ProductVariant.id,
        )
        .filter(
            ProductVariant.product_id == product.id,
        )
        .all()
    )

    variant_responses = []

    for variant, inventory in variants:
        available_quantity = 0

        if (
            variant.is_active
            and inventory is not None
            and inventory.is_active
        ):
            available_quantity = max(
                inventory.quantity - inventory.reserved_quantity,
                0,
            )

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