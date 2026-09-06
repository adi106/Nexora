from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from backend.app.core.security import require_role
from backend.app.db.dependencies import get_db
from backend.app.models.category import Category
from backend.app.models.user import User
from backend.app.models.product import Product
from backend.app.services.category_service import (
    get_category_and_descendant_ids,
)
from backend.app.schemas.product import ProductListResponse
from backend.app.schemas.category import (
    CategoryCreate,
    CategoryResponse,
    CategoryStatusUpdate,
)


router = APIRouter(
    prefix="/categories",
    tags=["Categories"],
)


@router.get(
    "",
    response_model=list[CategoryResponse],
)
def list_categories(
    db: Session = Depends(get_db),
):
    categories = (
        db.query(Category)
        .filter(Category.is_active.is_(True))
        .order_by(Category.name.asc())
        .all()
    )

    return categories


@router.get(
    "/{category_id}",
    response_model=CategoryResponse,
)
def get_category(
    category_id: int,
    db: Session = Depends(get_db),
):
    category = (
        db.query(Category)
        .filter(
            Category.id == category_id,
            Category.is_active.is_(True),
        )
        .first()
    )

    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )

    return category


@router.get(
    "/{slug}/products",
    response_model=ProductListResponse,
)
def list_category_products(
    slug: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    category = (
        db.query(Category)
        .filter(
            Category.slug == slug,
            Category.is_active.is_(True),
        )
        .first()
    )

    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )

    category_ids = get_category_and_descendant_ids(
        category,
        db,
    )

    query = (
        db.query(Product)
        .join(Category, Product.category_id == Category.id)
        .filter(
            Product.category_id.in_(category_ids),
            Product.is_active.is_(True),
            Category.is_active.is_(True),
        )
        .order_by(Product.created_at.desc())
    )

    total = query.count()

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


@router.post(
    "",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_category(
    category_data: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    existing_category = (
        db.query(Category)
        .filter(Category.slug == category_data.slug)
        .first()
    )

    if existing_category:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Category slug already exists",
        )

    category = Category(
        name=category_data.name,
        slug=category_data.slug,
        description=category_data.description,
        parent_id=category_data.parent_id,
    )

    db.add(category)
    db.commit()
    db.refresh(category)

    return category

@router.patch(
    "/{category_id}",
    response_model=CategoryResponse,
)
def update_category_status(
    category_id: int,
    category_data: CategoryStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    category = (
        db.query(Category)
        .filter(Category.id == category_id)
        .first()
    )

    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )

    category.is_active = category_data.is_active

    db.commit()
    db.refresh(category)

    return category