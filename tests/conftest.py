from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import Session

from backend.app.core.security import hash_password
from backend.app.db.dependencies import get_db
from backend.app.main import app
from backend.app.models import (
    Address,
    Cart,
    CartItem,
    Category,
    Inventory,
    Order,
    OrderItem,
    Product,
    ProductVariant,
    Role,
    Seller,
    User,
    UserRole,
)
from backend.app.models.cart import CartStatus


TEST_DATABASE_URL = (
    "postgresql+psycopg://nexora:"
    "nexora_dev_password@localhost:5432/nexora_test"
)

test_engine = create_engine(
    TEST_DATABASE_URL,
    pool_pre_ping=True,
)


@pytest.fixture(scope="session", autouse=True)
def seed_test_database():
    db = Session(test_engine)

    try:
        user = db.scalar(
            select(User).where(
                User.email == "secure.test@nexora.com"
            )
        )

        if user is None:
            user = User(
                email="secure.test@nexora.com",
                password_hash=hash_password("TestPassword123!"),
                first_name="Secure",
                last_name="Test",
            )
            db.add(user)
            db.flush()

        customer_role = db.scalar(
            select(Role).where(
                Role.name == "customer"
            )
        )

        if customer_role is not None:
            existing_user_role = db.scalar(
                select(UserRole).where(
                    UserRole.user_id == user.id,
                    UserRole.role_id == customer_role.id,
                )
            )

            if existing_user_role is None:
                db.add(
                    UserRole(
                        user_id=user.id,
                        role_id=customer_role.id,
                    )
                )

        seller_user = db.scalar(
            select(User).where(
                User.email == "test.seller@nexora.local"
            )
        )

        if seller_user is None:
            seller_user = User(
                email="test.seller@nexora.local",
                password_hash=hash_password("TestPassword123!"),
                first_name="Test",
                last_name="Seller",
            )
            db.add(seller_user)
            db.flush()

        seller_role = db.scalar(
            select(Role).where(
                Role.name == "seller"
            )
        )

        if seller_role is not None:
            existing_seller_role = db.scalar(
                select(UserRole).where(
                    UserRole.user_id == seller_user.id,
                    UserRole.role_id == seller_role.id,
                )
            )

            if existing_seller_role is None:
                db.add(
                    UserRole(
                        user_id=seller_user.id,
                        role_id=seller_role.id,
                    )
                )

        seller = db.scalar(
            select(Seller).where(
                Seller.user_id == seller_user.id
            )
        )

        if seller is None:
            seller = Seller(
                user_id=seller_user.id,
                store_name="NEXORA Test Store",
                store_slug="nexora-test-store",
                description="Development test seller",
            )
            db.add(seller)
            db.flush()

        category = db.scalar(
            select(Category).where(
                Category.slug == "laptops"
            )
        )

        if category is None:
            category = Category(
                name="Laptops",
                slug="laptops",
                description="Laptop computers",
            )
            db.add(category)
            db.flush()

        product = db.scalar(
            select(Product).where(
                Product.slug == "nexora-pro-laptop"
            )
        )

        if product is None:
            product = Product(
                seller_id=seller.id,
                category_id=category.id,
                name="NEXORA Pro Laptop",
                slug="nexora-pro-laptop",
                description="Development test product",
                base_price=Decimal("1299.99"),
            )
            db.add(product)
            db.flush()

        variant = db.scalar(
            select(ProductVariant).where(
                ProductVariant.sku == "NEXORA-PRO-16-512"
            )
        )

        if variant is None:
            variant = ProductVariant(
                product_id=product.id,
                sku="NEXORA-PRO-16-512",
                price=Decimal("1399.99"),
                attributes={
                    "color": "Silver",
                    "ram": "16GB",
                    "storage": "512GB",
                },
            )
            db.add(variant)
            db.flush()

        inventory = db.scalar(
            select(Inventory).where(
                Inventory.variant_id == variant.id
            )
        )

        if inventory is None:
            inventory = Inventory(
                variant_id=variant.id,
                quantity=100,
                reserved_quantity=0,
                reorder_level=5,
            )
            db.add(inventory)

        address = db.scalar(
            select(Address).where(
                Address.user_id == user.id
            )
        )

        if address is None:
            address = Address(
                user_id=user.id,
                address_line1="123 Victoria Street",
                address_line2=None,
                city="Hamilton",
                region="Waikato",
                postal_code="3204",
                country_code="NZ",
                is_default=True,
            )
            db.add(address)

        cart = db.scalar(
            select(Cart).where(
                Cart.user_id == user.id,
                Cart.status == CartStatus.ACTIVE,
            )
        )

        if cart is None:
            cart = Cart(
                user_id=user.id,
                status=CartStatus.ACTIVE,
            )
            db.add(cart)

        db.commit()

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


@pytest.fixture
def test_db():
    db = Session(test_engine)

    try:
        yield db
    finally:
        db.rollback()
        db.close()


@pytest.fixture(autouse=True)
def reset_order_state(test_db):
    user = test_db.scalar(
        select(User).where(
            User.email == "secure.test@nexora.com"
        )
    )

    assert user is not None

    cart = test_db.scalar(
        select(Cart).where(
            Cart.user_id == user.id,
            Cart.status == CartStatus.ACTIVE,
        )
    )

    if cart is None:
        cart = Cart(
            user_id=user.id,
            status=CartStatus.ACTIVE,
        )
        test_db.add(cart)
        test_db.flush()

    # Remove cart items from previous tests.
    test_db.execute(
        delete(CartItem).where(
            CartItem.cart_id == cart.id
        )
    )

    # Remove previous test orders.
    order_ids = select(Order.id).where(
        Order.user_id == user.id
    )

    test_db.execute(
        delete(OrderItem).where(
            OrderItem.order_id.in_(order_ids)
        )
    )

    test_db.execute(
        delete(Order).where(
            Order.user_id == user.id
        )
    )

    # Restore deterministic inventory state.
    variant = test_db.scalar(
        select(ProductVariant).where(
            ProductVariant.sku == "NEXORA-PRO-16-512"
        )
    )

    assert variant is not None

    inventory = test_db.scalar(
        select(Inventory).where(
            Inventory.variant_id == variant.id
        )
    )

    assert inventory is not None

    inventory.quantity = 100
    inventory.reserved_quantity = 0

    cart.status = CartStatus.ACTIVE

    test_db.commit()


@pytest.fixture
def client():
    def override_get_db():
        db = Session(test_engine)

        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()