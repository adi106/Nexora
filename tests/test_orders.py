from sqlalchemy import select

from backend.app.models import (
    Address,
    Cart,
    CartItem,
    Inventory,
    ProductVariant,
    User,
)
from backend.app.models.cart import CartStatus


TEST_EMAIL = "secure.test@nexora.com"
TEST_PASSWORD = "TestPassword123!"
TEST_SKU = "NEXORA-PRO-16-512"


def login(client):
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": TEST_EMAIL,
            "password": TEST_PASSWORD,
        },
    )

    assert response.status_code == 200

    return response.json()["access_token"]


def get_test_variant(test_db):
    variant = test_db.scalar(
        select(ProductVariant).where(
            ProductVariant.sku == TEST_SKU
        )
    )

    assert variant is not None

    return variant


def get_test_user(test_db):
    user = test_db.scalar(
        select(User).where(
            User.email == TEST_EMAIL
        )
    )

    assert user is not None

    return user


def get_test_address(test_db):
    user = get_test_user(test_db)

    address = test_db.scalar(
        select(Address).where(
            Address.user_id == user.id
        )
    )

    assert address is not None

    return address


def get_test_cart(test_db):
    user = get_test_user(test_db)

    cart = test_db.scalar(
        select(Cart).where(
            Cart.user_id == user.id,
            Cart.status == CartStatus.ACTIVE,
        )
    )

    assert cart is not None

    return cart


def test_create_order_requires_authentication(client, test_db):
    address = get_test_address(test_db)

    response = client.post(
        "/api/v1/orders",
        json={
            "address_id": str(address.id),
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_get_orders_requires_authentication(client):
    response = client.get(
        "/api/v1/orders"
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_get_single_order_requires_authentication(client):
    response = client.get(
        "/api/v1/orders/3481b84c-0de6-45a9-8dbb-e3f57ec6d3f5"
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_create_order_with_authenticated_user(client, test_db):
    token = login(client)

    variant = get_test_variant(test_db)
    address = get_test_address(test_db)

    cart_response = client.get(
        "/api/v1/cart",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert cart_response.status_code == 200

    add_response = client.post(
        "/api/v1/cart/items",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "variant_id": str(variant.id),
            "quantity": 1,
        },
    )

    assert add_response.status_code == 201

    order_response = client.post(
        "/api/v1/orders",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "address_id": str(address.id),
        },
    )

    assert order_response.status_code == 201

    data = order_response.json()

    assert "id" in data
    assert data["status"] == "pending"
    assert data["total_amount"] == "1399.99"
    assert data["shipping_full_name"] == "Secure Test"
    assert data["shipping_city"] == "Hamilton"
    assert data["shipping_country_code"] == "NZ"

    assert len(data["items"]) == 1
    assert data["items"][0]["sku"] == TEST_SKU
    assert data["items"][0]["quantity"] == 1
    assert data["items"][0]["subtotal"] == "1399.99"


def test_create_order_reserves_inventory(client, test_db):
    token = login(client)

    variant = get_test_variant(test_db)
    address = get_test_address(test_db)

    inventory = test_db.scalar(
        select(Inventory).where(
            Inventory.variant_id == variant.id
        )
    )

    assert inventory is not None

    reserved_before = inventory.reserved_quantity

    add_response = client.post(
        "/api/v1/cart/items",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "variant_id": str(variant.id),
            "quantity": 2,
        },
    )

    assert add_response.status_code == 201

    order_response = client.post(
        "/api/v1/orders",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "address_id": str(address.id),
        },
    )

    assert order_response.status_code == 201

    data = order_response.json()

    assert data["status"] == "pending"
    assert data["items"][0]["quantity"] == 2

    test_db.expire_all()

    inventory = test_db.scalar(
        select(Inventory).where(
            Inventory.variant_id == variant.id
        )
    )

    assert inventory is not None
    assert inventory.reserved_quantity == reserved_before + 2


def test_create_order_rejects_insufficient_stock(client, test_db):
    token = login(client)

    variant = get_test_variant(test_db)
    address = get_test_address(test_db)

    inventory = test_db.scalar(
        select(Inventory).where(
            Inventory.variant_id == variant.id
        )
    )

    assert inventory is not None

    available_stock = (
        inventory.quantity - inventory.reserved_quantity
    )

    requested_quantity = available_stock + 1

    add_response = client.post(
        "/api/v1/cart/items",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "variant_id": str(variant.id),
            "quantity": 1,
        },
    )

    assert add_response.status_code == 201

    cart = get_test_cart(test_db)

    cart_item = test_db.scalar(
        select(CartItem).where(
            CartItem.cart_id == cart.id,
            CartItem.variant_id == variant.id,
        )
    )

    assert cart_item is not None

    # Deliberately bypass the cart API's stock validation.
    # This tests the checkout service's own stock protection.
    cart_item.quantity = requested_quantity

    test_db.commit()

    order_response = client.post(
        "/api/v1/orders",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "address_id": str(address.id),
        },
    )

    assert order_response.status_code == 400
    assert "items available" in order_response.json()["detail"]


def test_payment_success_updates_order_and_inventory(client, test_db):
    token = login(client)

    variant = get_test_variant(test_db)
    address = get_test_address(test_db)

    inventory = test_db.scalar(
        select(Inventory).where(
            Inventory.variant_id == variant.id
        )
    )

    assert inventory is not None

    quantity_before = inventory.quantity
    reserved_before = inventory.reserved_quantity

    add_response = client.post(
        "/api/v1/cart/items",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "variant_id": str(variant.id),
            "quantity": 1,
        },
    )

    assert add_response.status_code == 201

    order_response = client.post(
        "/api/v1/orders",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "address_id": str(address.id),
        },
    )

    assert order_response.status_code == 201

    order_id = order_response.json()["id"]

    payment_response = client.post(
        f"/api/v1/orders/{order_id}/payment",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "succeed": True,
        },
    )

    assert payment_response.status_code == 200

    data = payment_response.json()

    assert data["status"] == "paid"

    test_db.expire_all()

    inventory = test_db.scalar(
        select(Inventory).where(
            Inventory.variant_id == variant.id
        )
    )

    assert inventory is not None

    assert inventory.quantity == quantity_before - 1
    assert inventory.reserved_quantity == reserved_before


def test_payment_failure_cancels_order_and_releases_inventory(
    client,
    test_db,
):
    token = login(client)

    variant = get_test_variant(test_db)
    address = get_test_address(test_db)

    inventory = test_db.scalar(
        select(Inventory).where(
            Inventory.variant_id == variant.id
        )
    )

    assert inventory is not None

    quantity_before = inventory.quantity
    reserved_before = inventory.reserved_quantity

    add_response = client.post(
        "/api/v1/cart/items",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "variant_id": str(variant.id),
            "quantity": 1,
        },
    )

    assert add_response.status_code == 201

    order_response = client.post(
        "/api/v1/orders",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "address_id": str(address.id),
        },
    )

    assert order_response.status_code == 201

    order_id = order_response.json()["id"]

    payment_response = client.post(
        f"/api/v1/orders/{order_id}/payment",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "succeed": False,
        },
    )

    assert payment_response.status_code == 200

    data = payment_response.json()

    assert data["status"] == "cancelled"

    test_db.expire_all()

    inventory = test_db.scalar(
        select(Inventory).where(
            Inventory.variant_id == variant.id
        )
    )

    assert inventory is not None

    assert inventory.quantity == quantity_before
    assert inventory.reserved_quantity == reserved_before