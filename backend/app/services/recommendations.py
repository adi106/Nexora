import uuid

from sqlalchemy import func
from sqlalchemy.orm import Session, aliased

from backend.app.models.order import Order, OrderStatus
from backend.app.models.order_item import OrderItem
from backend.app.models.product import Product
from backend.app.models.product_variant import ProductVariant
from backend.app.models.wishlist import WishlistItem


_FULFILLED_STATUSES = [
    OrderStatus.PAID,
    OrderStatus.SHIPPED,
    OrderStatus.DELIVERED,
]


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


def get_similar_products(
    db: Session,
    product_id: uuid.UUID,
    limit: int = 10,
) -> list[Product]:
    """
    Item-based collaborative filtering: "customers who bought this also
    bought" other products, ranked by co-occurrence in fulfilled orders.

    Falls back to same-category products, then overall popularity, when
    there isn't enough co-purchase data yet (cold start).
    """

    orders_with_product = (
        db.query(Order.id)
        .join(OrderItem, OrderItem.order_id == Order.id)
        .join(ProductVariant, OrderItem.variant_id == ProductVariant.id)
        .filter(
            ProductVariant.product_id == product_id,
            Order.status.in_(_FULFILLED_STATUSES),
        )
        .distinct()
    )

    other_variant = aliased(ProductVariant)
    other_order_item = aliased(OrderItem)

    co_purchase_counts = (
        db.query(
            Product.id,
            func.count(func.distinct(other_order_item.order_id)).label("co_occurrence"),
        )
        .join(other_variant, other_variant.product_id == Product.id)
        .join(other_order_item, other_order_item.variant_id == other_variant.id)
        .filter(
            other_order_item.order_id.in_(orders_with_product),
            Product.id != product_id,
            Product.is_active.is_(True),
        )
        .group_by(Product.id)
        .order_by(func.count(func.distinct(other_order_item.order_id)).desc())
        .limit(limit)
        .all()
    )

    ordered_ids = [pid for pid, _count in co_purchase_counts]
    similar: list[Product] = []

    if ordered_ids:
        products_by_id = {
            product.id: product
            for product in db.query(Product).filter(Product.id.in_(ordered_ids)).all()
        }
        similar = [products_by_id[pid] for pid in ordered_ids if pid in products_by_id]

    if len(similar) >= limit:
        return similar[:limit]

    seen_ids = {product.id for product in similar}

    source_product = db.query(Product).filter(Product.id == product_id).first()
    if source_product is not None:
        same_category = (
            db.query(Product)
            .filter(
                Product.category_id == source_product.category_id,
                Product.id != product_id,
                Product.is_active.is_(True),
                ~Product.id.in_(seen_ids) if seen_ids else True,
            )
            .order_by(Product.created_at.desc())
            .limit(limit - len(similar))
            .all()
        )
        for product in same_category:
            if product.id not in seen_ids:
                similar.append(product)
                seen_ids.add(product.id)

    if len(similar) >= limit:
        return similar[:limit]

    for product in get_popular_products(db, limit=limit):
        if product.id != product_id and product.id not in seen_ids:
            similar.append(product)
            seen_ids.add(product.id)
        if len(similar) >= limit:
            break

    return similar