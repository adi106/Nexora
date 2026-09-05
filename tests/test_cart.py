def test_get_cart_authenticated(client):
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "secure.test@nexora.com",
            "password": "TestPassword123!",
        },
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

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
    response = client.get("/api/v1/cart")

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"

def test_add_cart_item(client):
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "secure.test@nexora.com",
            "password": "TestPassword123!",
        },
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    response = client.post(
        "/api/v1/cart/items",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "variant_id": "2c3f7cd0-9d7a-4a5d-aafd-887806c0d1d9",
            "quantity": 1,
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["variant_id"] == "2c3f7cd0-9d7a-4a5d-aafd-887806c0d1d9"
    assert data["quantity"] >= 1

def test_add_nonexistent_variant(client):
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "secure.test@nexora.com",
            "password": "TestPassword123!",
        },
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

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

def test_add_cart_item_exceeds_stock(client):
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "secure.test@nexora.com",
            "password": "TestPassword123!",
        },
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    response = client.post(
        "/api/v1/cart/items",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "variant_id": "2c3f7cd0-9d7a-4a5d-aafd-887806c0d1d9",
            "quantity": 23,
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Only 22 items available"

def test_update_cart_item(client):
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "secure.test@nexora.com",
            "password": "TestPassword123!",
        },
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    add_response = client.post(
        "/api/v1/cart/items",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "variant_id": "2c3f7cd0-9d7a-4a5d-aafd-887806c0d1d9",
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
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "secure.test@nexora.com",
            "password": "TestPassword123!",
        },
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

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

def test_update_cart_item_exceeds_stock(client):
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "secure.test@nexora.com",
            "password": "TestPassword123!",
        },
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    add_response = client.post(
        "/api/v1/cart/items",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "variant_id": "2c3f7cd0-9d7a-4a5d-aafd-887806c0d1d9",
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
            "quantity": 23,
        },
    )

    assert update_response.status_code == 400
    assert update_response.json()["detail"] == "Only 22 items available"

def test_delete_cart_item(client):
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "secure.test@nexora.com",
            "password": "TestPassword123!",
        },
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    add_response = client.post(
        "/api/v1/cart/items",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "variant_id": "2c3f7cd0-9d7a-4a5d-aafd-887806c0d1d9",
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
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "secure.test@nexora.com",
            "password": "TestPassword123!",
        },
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    response = client.delete(
        "/api/v1/cart/items/00000000-0000-0000-0000-000000000000",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Cart item not found"