import uuid
from decimal import Decimal

from sqlalchemy import select

from backend.app.models import (
    Category,
    Inventory,
    Order,
    OrderItem,
    OrderStatus,
    Product,
    ProductVariant,
    Seller,
    User,
)
from backend.app.services.recommendations import get_similar_products


TEST_PASSWORD = "TestPassword123!"
BUYER_EMAIL = "secure.test@nexora.com"


def login(client, email):
    response = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": TEST_PASSWORD},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def make_product(test_db, seller_id, category_id, name):
    unique = uuid.uuid4().hex[:10]
    product = Product(
        seller_id=seller_id,
        category_id=category_id,
        name=name,
        slug=f"{name.lower().replace(' ', '-')}-{unique}",
        description="Test product",
        base_price=Decimal("50.00"),
    )
    test_db.add(product)
    test_db.flush()

    variant = ProductVariant(
        product_id=product.id,
        sku=f"SKU-{unique}",
        price=Decimal("50.00"),
        attributes={},
    )
    test_db.add(variant)
    test_db.flush()

    test_db.add(
        Inventory(variant_id=variant.id, quantity=100, reserved_quantity=0, reorder_level=5)
    )
    test_db.flush()

    return product, variant


def place_fulfilled_order(test_db, user_id, variants_and_quantities):
    order = Order(
        user_id=user_id,
        status=OrderStatus.DELIVERED,
        total_amount=Decimal("0.00"),
        shipping_full_name="Test Buyer",
        shipping_address_line1="1 Test St",
        shipping_address_line2=None,
        shipping_city="Testville",
        shipping_region=None,
        shipping_postal_code="00000",
        shipping_country_code="US",
    )
    test_db.add(order)
    test_db.flush()

    for variant, quantity in variants_and_quantities:
        test_db.add(
            OrderItem(
                order_id=order.id,
                variant_id=variant.id,
                product_name=variant.sku,
                sku=variant.sku,
                unit_price=variant.price,
                quantity=quantity,
                subtotal=variant.price * quantity,
            )
        )

    test_db.commit()
    return order


def test_similar_products_ranks_by_co_purchase(client, test_db):
    seller = test_db.scalar(select(Seller).where(Seller.store_slug == "nexora-test-store"))
    category = test_db.scalar(select(Category).where(Category.slug == "laptops"))
    buyer = test_db.scalar(select(User).where(User.email == BUYER_EMAIL))

    product_a, variant_a = make_product(test_db, seller.id, category.id, "Similar Base")
    product_b, variant_b = make_product(test_db, seller.id, category.id, "Similar CoBought")
    product_c, variant_c = make_product(test_db, seller.id, category.id, "Similar Unrelated")

    place_fulfilled_order(test_db, buyer.id, [(variant_a, 1), (variant_b, 1)])

    similar = get_similar_products(test_db, product_a.id, limit=10)
    similar_ids = [p.id for p in similar]

    assert product_b.id in similar_ids
    assert product_a.id not in similar_ids


def test_similar_products_falls_back_to_category_when_no_co_purchases(client, test_db):
    seller = test_db.scalar(select(Seller).where(Seller.store_slug == "nexora-test-store"))
    category = test_db.scalar(select(Category).where(Category.slug == "laptops"))

    product_a, _variant_a = make_product(test_db, seller.id, category.id, "Cold Start Base")
    product_b, _variant_b = make_product(test_db, seller.id, category.id, "Cold Start Peer")

    similar = get_similar_products(test_db, product_a.id, limit=10)
    similar_ids = [p.id for p in similar]

    assert product_b.id in similar_ids
    assert all(p.category_id == category.id for p in similar)


def test_similar_products_endpoint_public_and_excludes_source(client, test_db):
    seller = test_db.scalar(select(Seller).where(Seller.store_slug == "nexora-test-store"))
    category = test_db.scalar(select(Category).where(Category.slug == "laptops"))

    product_a, _variant_a = make_product(test_db, seller.id, category.id, "Endpoint Base")
    test_db.commit()

    response = client.get(f"/api/v1/recommendations/similar/{product_a.id}")

    assert response.status_code == 200
    ids = [item["id"] for item in response.json()]
    assert str(product_a.id) not in ids


def test_similar_products_endpoint_404_for_unknown_product(client):
    response = client.get(f"/api/v1/recommendations/similar/{uuid.uuid4()}")
    assert response.status_code == 404
