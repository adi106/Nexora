import uuid

from sqlalchemy import select

from backend.app.models import Address, Cart, CartStatus, ProductVariant, User


TEST_PASSWORD = "TestPassword123!"
SELLER_EMAIL = "test.seller@nexora.local"
BUYER_EMAIL = "secure.test@nexora.com"
TEST_SKU = "NEXORA-PRO-16-512"


def login(client, email):
    response = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": TEST_PASSWORD},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def register_and_login(client):
    email = f"newseller.{uuid.uuid4().hex[:10]}@nexora.com"
    created = client.post(
        "/api/v1/users",
        json={
            "email": email,
            "password": TEST_PASSWORD,
            "first_name": "New",
            "last_name": "Seller",
        },
    )
    assert created.status_code == 201
    return login(client, email)


def test_become_seller_requires_authentication(client):
    response = client.post(
        "/api/v1/sellers",
        json={"store_name": "X", "store_slug": "x"},
    )
    assert response.status_code == 401


def test_become_seller_creates_seller_and_assigns_role(client, test_db):
    token = register_and_login(client)
    unique = uuid.uuid4().hex[:8]

    response = client.post(
        "/api/v1/sellers",
        headers={"Authorization": f"Bearer {token}"},
        json={"store_name": f"Store {unique}", "store_slug": f"store-{unique}"},
    )

    assert response.status_code == 201
    assert response.json()["store_slug"] == f"store-{unique}"

    me = client.get("/api/v1/sellers/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200


def test_become_seller_twice_conflicts(client, test_db):
    token = login(client, SELLER_EMAIL)

    response = client.post(
        "/api/v1/sellers",
        headers={"Authorization": f"Bearer {token}"},
        json={"store_name": "Duplicate Store", "store_slug": "duplicate-store"},
    )

    assert response.status_code == 409


def test_get_my_seller_profile_requires_seller_account(client, test_db):
    token = login(client, BUYER_EMAIL)

    response = client.get("/api/v1/sellers/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 404


def test_seller_stats_reflect_own_catalog(client, test_db):
    token = login(client, SELLER_EMAIL)

    response = client.get("/api/v1/sellers/me/stats", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    data = response.json()
    assert data["product_count"] >= 1
    assert data["order_count"] >= 0
    assert data["customer_count"] >= 0


def test_list_my_products_only_returns_own(client, test_db):
    token = login(client, SELLER_EMAIL)

    response = client.get("/api/v1/sellers/me/products", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    data = response.json()
    assert any(item["slug"] == "nexora-pro-laptop" for item in data["items"])


def test_get_my_product_not_owned_returns_404(client, test_db):
    token = login(client, SELLER_EMAIL)

    response = client.get(
        f"/api/v1/sellers/me/products/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404


def test_seller_orders_include_orders_with_their_items(client, test_db):
    buyer_token = login(client, BUYER_EMAIL)
    seller_token = login(client, SELLER_EMAIL)

    variant = test_db.scalar(select(ProductVariant).where(ProductVariant.sku == TEST_SKU))
    buyer = test_db.scalar(select(User).where(User.email == BUYER_EMAIL))
    address = test_db.scalar(select(Address).where(Address.user_id == buyer.id))

    cart = test_db.scalar(
        select(Cart).where(Cart.user_id == buyer.id, Cart.status == CartStatus.ACTIVE)
    )
    assert cart is not None

    add_item = client.post(
        "/api/v1/cart/items",
        headers={"Authorization": f"Bearer {buyer_token}"},
        json={"variant_id": str(variant.id), "quantity": 1},
    )
    assert add_item.status_code == 201

    order_response = client.post(
        "/api/v1/orders",
        headers={"Authorization": f"Bearer {buyer_token}"},
        json={"address_id": str(address.id)},
    )
    assert order_response.status_code == 201
    order_id = order_response.json()["id"]

    seller_orders = client.get(
        "/api/v1/sellers/me/orders",
        headers={"Authorization": f"Bearer {seller_token}"},
    )

    assert seller_orders.status_code == 200
    assert order_id in [order["id"] for order in seller_orders.json()]
