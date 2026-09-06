import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.core.security import get_current_user
from backend.app.db.dependencies import get_db
from backend.app.models.product import Product
from backend.app.models.wishlist import WishlistItem
from backend.app.schemas.wishlist import WishlistItemResponse


router = APIRouter(prefix="/wishlist", tags=["wishlist"])


@router.post(
    "/products/{product_id}",
    response_model=WishlistItemResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_to_wishlist(
    product_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    product = db.scalar(
        select(Product).where(
            Product.id == product_id,
            Product.is_active.is_(True),
        )
    )

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    existing_item = db.scalar(
        select(WishlistItem).where(
            WishlistItem.user_id == current_user.id,
            WishlistItem.product_id == product_id,
        )
    )

    if existing_item is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Product is already in the wishlist",
        )

    wishlist_item = WishlistItem(
        user_id=current_user.id,
        product_id=product_id,
    )

    db.add(wishlist_item)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Product is already in the wishlist",
        )

    db.refresh(wishlist_item)

    return wishlist_item


@router.get(
    "",
    response_model=list[WishlistItemResponse],
)
def get_wishlist(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    wishlist_items = db.scalars(
        select(WishlistItem)
        .where(WishlistItem.user_id == current_user.id)
        .order_by(WishlistItem.created_at.desc())
    ).all()

    return wishlist_items


@router.delete(
    "/products/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_from_wishlist(
    product_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    wishlist_item = db.scalar(
        select(WishlistItem).where(
            WishlistItem.user_id == current_user.id,
            WishlistItem.product_id == product_id,
        )
    )

    if wishlist_item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wishlist item not found",
        )

    db.delete(wishlist_item)
    db.commit()

    return None