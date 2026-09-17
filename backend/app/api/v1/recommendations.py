from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.core.security import get_current_user
from backend.app.db.dependencies import get_db
from backend.app.models.category import Category
from backend.app.models.product import Product
from backend.app.models.product_interaction import ProductInteraction
from backend.app.models.user import User
from backend.app.schemas.product import ProductResponse
from backend.app.services.recommendations import get_recommendations, get_similar_products
from backend.app.schemas.recommendation import (
    ProductInteractionCreate,
    ProductInteractionResponse,
)

router = APIRouter(
    prefix="/recommendations",
    tags=["Recommendations"],
)

@router.get(
    "",
    response_model=list[ProductResponse],
)
def get_product_recommendations(
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_recommendations(
        db,
        current_user.id,
        limit=limit,
    )


@router.get(
    "/similar/{product_id}",
    response_model=list[ProductResponse],
)
def get_similar_product_recommendations(
    product_id: UUID,
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
):
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
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    return get_similar_products(db, product_id, limit=limit)


@router.post(
    "/interactions",
    response_model=ProductInteractionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_product_interaction(
    interaction_data: ProductInteractionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    product = (
        db.query(Product)
        .filter(
            Product.id == interaction_data.product_id,
            Product.is_active.is_(True),
        )
        .first()
    )

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    interaction = ProductInteraction(
        user_id=current_user.id,
        product_id=interaction_data.product_id,
        interaction_type=interaction_data.interaction_type,
    )

    db.add(interaction)
    db.commit()
    db.refresh(interaction)

    return interaction