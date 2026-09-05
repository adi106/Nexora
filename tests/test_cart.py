from sqlalchemy import select

from backend.app.models import Inventory, ProductVariant


TEST_SKU = "NEXORA-PRO-16-512"


def login(client):
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "secure.test@nexora.com",
            "password": "TestPassword123!",
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


def get_test_inventory(test_db, variant_id):
    inventory = test_db.scalar(
        select(Inventory).where(
            Inventory.variant_id == variant_id
        )
    )

    assert inventory is not None

    return inventory


def test_get_cart_authenticated(client):
    token = login(client)

    response = client.get(
        "/api/v1/cart",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert "id" in data
    assert data["status"] == "active"
    assert "items" in data


def test_get_cart_unauthenticated(client):
    response = client.get(
        "/api/v1/cart"
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_add_cart_item(client, test_db):
    token = login(client)
    variant = get_test_variant(test_db)

    response = client.post(
        "/api/v1/cart/items",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "variant_id": str(variant.id),
            "quantity": 1,
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["variant_id"] == str(variant.id)
    assert data["quantity"] == 1


def test_add_nonexistent_variant(client):
    token = login(client)

    response = client.post(
        "/api/v1/cart/items",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "variant_id": "00000000-0000-0000-0000-000000000000",
            "quantity": 1,
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Product variant not found"


def test_add_cart_item_exceeds_stock(client, test_db):
    token = login(client)

    variant = get_test_variant(test_db)
    inventory = get_test_inventory(test_db, variant.id)

    available_stock = (
        inventory.quantity - inventory.reserved_quantity
    )

    response = client.post(
        "/api/v1/cart/items",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "variant_id": str(variant.id),
            "quantity": available_stock + 1,
        },
    )

    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == f"Only {available_stock} items available"
    )


def test_update_cart_item(client, test_db):
    token = login(client)
    variant = get_test_variant(test_db)

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

    item_id = add_response.json()["id"]

    update_response = client.put(
        f"/api/v1/cart/items/{item_id}",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "quantity": 5,
        },
    )

    assert update_response.status_code == 200

    data = update_response.json()

    assert data["id"] == item_id
    assert data["quantity"] == 5


def test_update_nonexistent_cart_item(client):
    token = login(client)

    response = client.put(
        "/api/v1/cart/items/00000000-0000-0000-0000-000000000000",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "quantity": 2,
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Cart item not found"


def test_update_cart_item_exceeds_stock(client, test_db):
    token = login(client)
    variant = get_test_variant(test_db)

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

    item_id = add_response.json()["id"]

    inventory = get_test_inventory(test_db, variant.id)

    available_stock = (
        inventory.quantity - inventory.reserved_quantity
    )

    update_response = client.put(
        f"/api/v1/cart/items/{item_id}",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "quantity": available_stock + 1,
        },
    )

    assert update_response.status_code == 400
    assert (
        update_response.json()["detail"]
        == f"Only {available_stock} items available"
    )


def test_delete_cart_item(client, test_db):
    token = login(client)
    variant = get_test_variant(test_db)

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

    item_id = add_response.json()["id"]

    delete_response = client.delete(
        f"/api/v1/cart/items/{item_id}",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert delete_response.status_code == 204
    assert delete_response.content == b""


def test_delete_nonexistent_cart_item(client):
    token = login(client)

    response = client.delete(
        "/api/v1/cart/items/00000000-0000-0000-0000-000000000000",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Cart item not found"