from decimal import Decimal

from sqlalchemy import select

from backend.app.models.order import Order, OrderStatus
from backend.app.models.order_item import OrderItem
from backend.app.models.product import Product
from backend.app.models.product_variant import ProductVariant
from backend.app.models.user import User
from backend.app.models.wishlist import WishlistItem
from backend.app.services.recommendations import (
    get_newest_products,
    get_personalized_products,
    get_popular_products,
    get_recommendations,
)


def test_get_popular_products_returns_products_ranked_by_units_sold(
    test_db,
):
    user = test_db.scalar(
        select(User).where(
            User.email == "secure.test@nexora.com"
        )
    )

    assert user is not None

    variant = test_db.scalar(
        select(ProductVariant).where(
            ProductVariant.sku == "NEXORA-PRO-16-512"
        )
    )

    assert variant is not None

    product = test_db.scalar(
        select(Product).where(
            Product.id == variant.product_id
        )
    )

    assert product is not None

    order = Order(
        user_id=user.id,
        status=OrderStatus.DELIVERED,
        total_amount=Decimal("2799.98"),
        shipping_full_name="Secure Test",
        shipping_address_line1="123 Victoria Street",
        shipping_address_line2=None,
        shipping_city="Hamilton",
        shipping_region="Waikato",
        shipping_postal_code="3204",
        shipping_country_code="NZ",
    )

    test_db.add(order)
    test_db.flush()

    order_item = OrderItem(
        order_id=order.id,
        variant_id=variant.id,
        product_name=product.name,
        sku=variant.sku,
        unit_price=variant.price,
        quantity=2,
        subtotal=variant.price * 2,
    )

    test_db.add(order_item)
    test_db.commit()

    recommendations = get_popular_products(
        test_db,
        limit=10,
    )

    assert len(recommendations) == 1
    assert recommendations[0].id == product.id

def test_get_popular_products_ignores_cancelled_orders(
    test_db,
):
    user = test_db.scalar(
        select(User).where(
            User.email == "secure.test@nexora.com"
        )
    )

    assert user is not None

    variant = test_db.scalar(
        select(ProductVariant).where(
            ProductVariant.sku == "NEXORA-PRO-16-512"
        )
    )

    assert variant is not None

    product = test_db.scalar(
        select(Product).where(
            Product.id == variant.product_id
        )
    )

    assert product is not None

    order = Order(
        user_id=user.id,
        status=OrderStatus.CANCELLED,
        total_amount=Decimal("1399.99"),
        shipping_full_name="Secure Test",
        shipping_address_line1="123 Victoria Street",
        shipping_address_line2=None,
        shipping_city="Hamilton",
        shipping_region="Waikato",
        shipping_postal_code="3204",
        shipping_country_code="NZ",
    )

    test_db.add(order)
    test_db.flush()

    order_item = OrderItem(
        order_id=order.id,
        variant_id=variant.id,
        product_name=product.name,
        sku=variant.sku,
        unit_price=variant.price,
        quantity=10,
        subtotal=variant.price * 10,
    )

    test_db.add(order_item)
    test_db.commit()

    recommendations = get_popular_products(
        test_db,
        limit=10,
    )

    assert recommendations == []

def test_get_newest_products_returns_active_products(
    test_db,
):
    recommendations = get_newest_products(
        test_db,
        limit=10,
    )

    assert recommendations
    assert len(recommendations) <= 10
    assert all(
        product.is_active
        for product in recommendations
    )

def test_get_personalized_products_uses_purchase_category_affinity(
    test_db,
):
    user = test_db.scalar(
        select(User).where(
            User.email == "secure.test@nexora.com"
        )
    )

    assert user is not None

    variant = test_db.scalar(
        select(ProductVariant).where(
            ProductVariant.sku == "NEXORA-PRO-16-512"
        )
    )

    assert variant is not None

    purchased_product = test_db.scalar(
        select(Product).where(
            Product.id == variant.product_id
        )
    )

    assert purchased_product is not None

    order = Order(
        user_id=user.id,
        status=OrderStatus.DELIVERED,
        total_amount=variant.price * 2,
        shipping_full_name="Secure Test",
        shipping_address_line1="123 Victoria Street",
        shipping_address_line2=None,
        shipping_city="Hamilton",
        shipping_region="Waikato",
        shipping_postal_code="3204",
        shipping_country_code="NZ",
    )

    test_db.add(order)
    test_db.flush()

    order_item = OrderItem(
        order_id=order.id,
        variant_id=variant.id,
        product_name=purchased_product.name,
        sku=variant.sku,
        unit_price=variant.price,
        quantity=2,
        subtotal=variant.price * 2,
    )

    test_db.add(order_item)
    test_db.commit()

    recommendations = get_personalized_products(
        test_db,
        user.id,
        limit=10,
    )

    assert recommendations
    assert all(
        product.is_active
        for product in recommendations
    )

    assert all(
        product.id != purchased_product.id
        for product in recommendations
    )

    assert all(
        product.category_id == purchased_product.category_id
        for product in recommendations
    )

def test_get_personalized_products_uses_wishlist_category_affinity(
    test_db,
):
    user = test_db.scalar(
        select(User).where(
            User.email == "secure.test@nexora.com"
        )
    )

    assert user is not None

    variant = test_db.scalar(
        select(ProductVariant).where(
            ProductVariant.sku == "NEXORA-PRO-16-512"
        )
    )

    assert variant is not None

    wishlisted_product = test_db.scalar(
        select(Product).where(
            Product.id == variant.product_id
        )
    )

    assert wishlisted_product is not None

    wishlist_item = WishlistItem(
        user_id=user.id,
        product_id=wishlisted_product.id,
    )

    test_db.add(wishlist_item)
    test_db.commit()

    recommendations = get_personalized_products(
        test_db,
        user.id,
        limit=10,
    )

    assert recommendations
    assert all(
        product.is_active
        for product in recommendations
    )

    assert all(
        product.category_id == wishlisted_product.category_id
        for product in recommendations
    )

def test_get_recommendations_uses_personalized_products_first(
    test_db,
):
    user = test_db.scalar(
        select(User).where(
            User.email == "secure.test@nexora.com"
        )
    )

    assert user is not None

    variant = test_db.scalar(
        select(ProductVariant).where(
            ProductVariant.sku == "NEXORA-PRO-16-512"
        )
    )

    assert variant is not None

    purchased_product = test_db.scalar(
        select(Product).where(
            Product.id == variant.product_id
        )
    )

    assert purchased_product is not None

    order = Order(
        user_id=user.id,
        status=OrderStatus.DELIVERED,
        total_amount=variant.price,
        shipping_full_name="Secure Test",
        shipping_address_line1="123 Victoria Street",
        shipping_address_line2=None,
        shipping_city="Hamilton",
        shipping_region="Waikato",
        shipping_postal_code="3204",
        shipping_country_code="NZ",
    )

    test_db.add(order)
    test_db.flush()

    order_item = OrderItem(
        order_id=order.id,
        variant_id=variant.id,
        product_name=purchased_product.name,
        sku=variant.sku,
        unit_price=variant.price,
        quantity=1,
        subtotal=variant.price,
    )

    test_db.add(order_item)
    test_db.commit()

    recommendations = get_recommendations(
        test_db,
        user.id,
        limit=10,
    )

    assert recommendations
    assert all(
        product.category_id == purchased_product.category_id
        for product in recommendations
    )
    assert all(
        product.id != purchased_product.id
        for product in recommendations
    )

def test_get_recommendations_falls_back_to_newest_for_new_user(
    test_db,
):
    user = test_db.scalar(
        select(User).where(
            User.email == "other.test@nexora.com"
        )
    )

    assert user is not None

    recommendations = get_recommendations(
        test_db,
        user.id,
        limit=3,
    )

    assert recommendations
    assert len(recommendations) <= 3
    assert all(
        product.is_active
        for product in recommendations
    )