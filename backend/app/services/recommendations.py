from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.models.order import Order, OrderStatus
from backend.app.models.order_item import OrderItem
from backend.app.models.product import Product
from backend.app.models.product_variant import ProductVariant
from backend.app.models.wishlist import WishlistItem


def get_popular_products(
    db: Session,
    limit: int = 10,
) -> list[Product]:
    """
    Return active products ranked by the number of units sold.

    Only paid, shipped, and delivered orders contribute to popularity.
    """
    sold_quantity = func.coalesce(
        func.sum(OrderItem.quantity),
        0,
    ).label("sold_quantity")

    return (
        db.query(Product)
        .join(
            ProductVariant,
            ProductVariant.product_id == Product.id,
        )
        .join(
            OrderItem,
            OrderItem.variant_id == ProductVariant.id,
        )
        .join(
            Order,
            Order.id == OrderItem.order_id,
        )
        .filter(
            Product.is_active.is_(True),
            Order.status.in_(
                [
                    OrderStatus.PAID,
                    OrderStatus.SHIPPED,
                    OrderStatus.DELIVERED,
                ]
            ),
        )
        .group_by(Product.id)
        .order_by(
            sold_quantity.desc(),
            Product.created_at.desc(),
        )
        .limit(limit)
        .all()
    )


def get_newest_products(
    db: Session,
    limit: int = 10,
) -> list[Product]:
    """
    Return active products ordered by creation time.

    This acts as the final cold-start fallback when
    there is not enough behavioral or sales data.
    """
    return (
        db.query(Product)
        .filter(Product.is_active.is_(True))
        .order_by(Product.created_at.desc())
        .limit(limit)
        .all()
    )


def get_personalized_products(
    db: Session,
    user_id,
    limit: int = 10,
) -> list[Product]:
    """
    Return products from categories the user has shown interest in.

    User interest is currently inferred from:
    - completed purchases
    - wishlist additions

    Already purchased products are excluded.
    """

    purchased_product_ids = (
        db.query(Product.id)
        .join(
            ProductVariant,
            ProductVariant.product_id == Product.id,
        )
        .join(
            OrderItem,
            OrderItem.variant_id == ProductVariant.id,
        )
        .join(
            Order,
            Order.id == OrderItem.order_id,
        )
        .filter(
            Order.user_id == user_id,
            Order.status.in_(
                [
                    OrderStatus.PAID,
                    OrderStatus.SHIPPED,
                    OrderStatus.DELIVERED,
                ]
            ),
        )
        .distinct()
    )

    purchase_category_scores = (
        db.query(
            Product.category_id,
            func.sum(OrderItem.quantity).label("interest_score"),
        )
        .join(
            ProductVariant,
            ProductVariant.product_id == Product.id,
        )
        .join(
            OrderItem,
            OrderItem.variant_id == ProductVariant.id,
        )
        .join(
            Order,
            Order.id == OrderItem.order_id,
        )
        .filter(
            Order.user_id == user_id,
            Order.status.in_(
                [
                    OrderStatus.PAID,
                    OrderStatus.SHIPPED,
                    OrderStatus.DELIVERED,
                ]
            ),
        )
        .group_by(Product.category_id)
    )

    wishlist_category_scores = (
        db.query(
            Product.category_id,
            func.count(WishlistItem.id).label("interest_score"),
        )
        .join(
            WishlistItem,
            WishlistItem.product_id == Product.id,
        )
        .filter(
            WishlistItem.user_id == user_id,
        )
        .group_by(Product.category_id)
    )

    category_scores: dict[int, int] = {}

    for category_id, score in purchase_category_scores.all():
        category_scores[category_id] = (
            category_scores.get(category_id, 0) + score * 2
        )

    for category_id, score in wishlist_category_scores.all():
        category_scores[category_id] = (
            category_scores.get(category_id, 0) + score
        )

    if not category_scores:
        return []

    interested_categories = [
        category_id
        for category_id, _score in sorted(
            category_scores.items(),
            key=lambda item: item[1],
            reverse=True,
        )
    ]

    return (
        db.query(Product)
        .filter(
            Product.is_active.is_(True),
            Product.category_id.in_(interested_categories),
            ~Product.id.in_(purchased_product_ids),
        )
        .order_by(
            Product.created_at.desc(),
        )
        .limit(limit)
        .all()
    )

def get_recommendations(
    db: Session,
    user_id,
    limit: int = 10,
) -> list[Product]:
    """
    Return personalized product recommendations.

    Recommendation priority:
    1. Personalized category-based recommendations
    2. Popular products
    3. Newest products

    Products already purchased by the user are excluded
    from every recommendation stage.
    """

    personalized = get_personalized_products(
        db,
        user_id,
        limit=limit,
    )

    recommendations = list(personalized)
    recommended_ids = {
        product.id
        for product in recommendations
    }

    purchased_product_ids = {
        product_id
        for (product_id,) in (
            db.query(Product.id)
            .join(
                ProductVariant,
                ProductVariant.product_id == Product.id,
            )
            .join(
                OrderItem,
                OrderItem.variant_id == ProductVariant.id,
            )
            .join(
                Order,
                Order.id == OrderItem.order_id,
            )
            .filter(
                Order.user_id == user_id,
                Order.status.in_(
                    [
                        OrderStatus.PAID,
                        OrderStatus.SHIPPED,
                        OrderStatus.DELIVERED,
                    ]
                ),
            )
            .distinct()
            .all()
        )
    }

    if len(recommendations) >= limit:
        return recommendations[:limit]

    popular = get_popular_products(
        db,
        limit=limit,
    )

    for product in popular:
        if (
            product.id not in recommended_ids
            and product.id not in purchased_product_ids
        ):
            recommendations.append(product)
            recommended_ids.add(product.id)

        if len(recommendations) >= limit:
            return recommendations

    newest = get_newest_products(
        db,
        limit=limit,
    )

    for product in newest:
        if (
            product.id not in recommended_ids
            and product.id not in purchased_product_ids
        ):
            recommendations.append(product)
            recommended_ids.add(product.id)

        if len(recommendations) >= limit:
            return recommendations

    return recommendations