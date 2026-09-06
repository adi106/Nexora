from decimal import Decimal

from sqlalchemy import select

from backend.app.models.inventory import Inventory
from backend.app.models.product_variant import ProductVariant
from backend.app.models.product import Product
from backend.app.models.seller import Seller
from backend.app.models.user import User


def get_test_variant(test_db):
    variant = test_db.scalar(
        select(ProductVariant).where(
            ProductVariant.sku == "NEXORA-PRO-16-512"
        )
    )
    assert variant is not None
    return variant


def get_test_product(test_db):
    product = test_db.scalar(
        select(Product).where(
            Product.slug == "nexora-pro-laptop"
        )
    )
    assert product is not None
    return product


def test_seller_can_get_own_variant_inventory(client, test_db):
    variant = get_test_variant(test_db)

    token_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "test.seller@nexora.local",
            "password": "TestPassword123!",
        },
    )

    assert token_response.status_code == 200

    token = token_response.json()["access_token"]

    response = client.get(
        f"/api/v1/inventory/variants/{variant.id}",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["variant_id"] == str(variant.id)
    assert data["quantity"] == 100
    assert data["reserved_quantity"] == 0
    assert data["reorder_level"] == 5
    assert data["is_active"] is True


def test_seller_can_update_own_variant_inventory(client, test_db):
    variant = get_test_variant(test_db)

    token_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "test.seller@nexora.local",
            "password": "TestPassword123!",
        },
    )

    assert token_response.status_code == 200

    token = token_response.json()["access_token"]

    response = client.put(
        f"/api/v1/inventory/variants/{variant.id}",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "quantity": 75,
            "reorder_level": 10,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["quantity"] == 75
    assert data["reserved_quantity"] == 0
    assert data["reorder_level"] == 10

    inventory = test_db.scalar(
        select(Inventory).where(
            Inventory.variant_id == variant.id
        )
    )

    assert inventory is not None

    test_db.refresh(inventory)

    assert inventory.quantity == 75
    assert inventory.reorder_level == 10

    # Restore canonical inventory state.
    inventory.quantity = 100
    inventory.reserved_quantity = 0
    inventory.reorder_level = 5
    inventory.is_active = True
    test_db.commit()


def test_seller_can_update_inventory_status(client, test_db):
    variant = get_test_variant(test_db)

    token_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "test.seller@nexora.local",
            "password": "TestPassword123!",
        },
    )

    assert token_response.status_code == 200

    token = token_response.json()["access_token"]

    response = client.patch(
        f"/api/v1/inventory/variants/{variant.id}",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "is_active": False,
        },
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is False

    inventory = test_db.scalar(
        select(Inventory).where(
            Inventory.variant_id == variant.id
        )
    )

    assert inventory is not None

    test_db.refresh(inventory)

    assert inventory.is_active is False

    # Restore canonical state.
    inventory.is_active = True
    test_db.commit()


def test_inventory_requires_authentication(client, test_db):
    variant = get_test_variant(test_db)

    response = client.get(
        f"/api/v1/inventory/variants/{variant.id}"
    )

    assert response.status_code == 401


def test_customer_cannot_access_inventory(client, test_db):
    variant = get_test_variant(test_db)

    token_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "secure.test@nexora.com",
            "password": "TestPassword123!",
        },
    )

    assert token_response.status_code == 200

    token = token_response.json()["access_token"]

    response = client.get(
        f"/api/v1/inventory/variants/{variant.id}",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 403


def test_seller_cannot_access_another_sellers_inventory(
    client,
    test_db,
):
    variant = get_test_variant(test_db)
    product = get_test_product(test_db)

    other_user = test_db.scalar(
        select(User).where(
            User.email == "other.test.seller@nexora.local"
        )
    )

    assert other_user is not None

    other_seller = test_db.scalar(
        select(Seller).where(
            Seller.user_id == other_user.id
        )
    )

    assert other_seller is not None

    token_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "other.test.seller@nexora.local",
            "password": "TestPassword123!",
        },
    )

    assert token_response.status_code == 200

    token = token_response.json()["access_token"]

    response = client.get(
        f"/api/v1/inventory/variants/{variant.id}",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 404


def test_inventory_update_rejects_negative_quantity(
    client,
    test_db,
):
    variant = get_test_variant(test_db)

    token_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "test.seller@nexora.local",
            "password": "TestPassword123!",
        },
    )

    assert token_response.status_code == 200

    token = token_response.json()["access_token"]

    response = client.put(
        f"/api/v1/inventory/variants/{variant.id}",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "quantity": -1,
            "reorder_level": 5,
        },
    )

    assert response.status_code == 422


def test_inventory_update_rejects_negative_reorder_level(
    client,
    test_db,
):
    variant = get_test_variant(test_db)

    token_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "test.seller@nexora.local",
            "password": "TestPassword123!",
        },
    )

    assert token_response.status_code == 200

    token = token_response.json()["access_token"]

    response = client.put(
        f"/api/v1/inventory/variants/{variant.id}",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "quantity": 100,
            "reorder_level": -1,
        },
    )

    assert response.status_code == 422


def test_inventory_update_rejects_quantity_below_reserved_quantity(
    client,
    test_db,
):
    variant = get_test_variant(test_db)

    inventory = test_db.scalar(
        select(Inventory).where(
            Inventory.variant_id == variant.id
        )
    )

    assert inventory is not None

    inventory.quantity = 100
    inventory.reserved_quantity = 20
    test_db.commit()

    token_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "test.seller@nexora.local",
            "password": "TestPassword123!",
        },
    )

    assert token_response.status_code == 200

    token = token_response.json()["access_token"]

    response = client.put(
        f"/api/v1/inventory/variants/{variant.id}",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "quantity": 10,
            "reorder_level": 5,
        },
    )

    assert response.status_code == 400

    assert (
        response.json()["detail"]
        == "Quantity cannot be lower than the currently reserved quantity"
    )

    # Restore canonical state.
    test_db.refresh(inventory)
    inventory.quantity = 100
    inventory.reserved_quantity = 0
    inventory.reorder_level = 5
    inventory.is_active = True
    test_db.commit()


def test_inventory_not_found_for_nonexistent_variant(
    client,
    test_db,
):
    token_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "test.seller@nexora.local",
            "password": "TestPassword123!",
        },
    )

    assert token_response.status_code == 200

    token = token_response.json()["access_token"]

    response = client.get(
        "/api/v1/inventory/variants/00000000-0000-0000-0000-000000000000",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 404