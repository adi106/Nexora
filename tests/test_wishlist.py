import uuid

from sqlalchemy import select

from backend.app.models import Product, User
from backend.app.models.wishlist import WishlistItem


def get_auth_headers(client, email="secure.test@nexora.com"):
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": email,
            "password": "TestPassword123!",
        },
    )

    assert response.status_code == 200

    token = response.json()["access_token"]

    return {
        "Authorization": f"Bearer {token}",
    }


def test_add_product_to_wishlist(client, test_db):
    headers = get_auth_headers(client)

    product = test_db.scalar(
        select(Product).where(
            Product.slug == "nexora-pro-laptop",
        )
    )

    assert product is not None

    response = client.post(
        f"/api/v1/wishlist/products/{product.id}",
        headers=headers,
    )

    assert response.status_code == 201

    data = response.json()

    assert data["product_id"] == str(product.id)
    assert data["created_at"] is not None

    wishlist_item = test_db.scalar(
        select(WishlistItem).where(
            WishlistItem.product_id == product.id,
        )
    )

    assert wishlist_item is not None


def test_add_same_product_twice_returns_conflict(client, test_db):
    headers = get_auth_headers(client)

    product = test_db.scalar(
        select(Product).where(
            Product.slug == "nexora-pro-laptop",
        )
    )

    assert product is not None

    first_response = client.post(
        f"/api/v1/wishlist/products/{product.id}",
        headers=headers,
    )

    second_response = client.post(
        f"/api/v1/wishlist/products/{product.id}",
        headers=headers,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409
    assert second_response.json()["detail"] == (
        "Product is already in the wishlist"
    )


def test_add_nonexistent_product_returns_not_found(client):
    headers = get_auth_headers(client)

    product_id = uuid.uuid4()

    response = client.post(
        f"/api/v1/wishlist/products/{product_id}",
        headers=headers,
    )

    assert response.status_code == 404


def test_add_inactive_product_returns_not_found(client, test_db):
    headers = get_auth_headers(client)

    product = test_db.scalar(
        select(Product).where(
            Product.slug == "nexora-pro-laptop",
        )
    )

    assert product is not None

    product.is_active = False
    test_db.commit()

    response = client.post(
        f"/api/v1/wishlist/products/{product.id}",
        headers=headers,
    )

    assert response.status_code == 404


def test_get_wishlist_returns_current_users_items(client, test_db):
    headers = get_auth_headers(client)

    product = test_db.scalar(
        select(Product).where(
            Product.slug == "nexora-pro-laptop",
        )
    )

    assert product is not None

    add_response = client.post(
        f"/api/v1/wishlist/products/{product.id}",
        headers=headers,
    )

    assert add_response.status_code == 201

    response = client.get(
        "/api/v1/wishlist",
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["product_id"] == str(product.id)


def test_get_wishlist_requires_authentication(client):
    response = client.get("/api/v1/wishlist")

    assert response.status_code == 401


def test_add_to_wishlist_requires_authentication(client, test_db):
    product = test_db.scalar(
        select(Product).where(
            Product.slug == "nexora-pro-laptop",
        )
    )

    assert product is not None

    response = client.post(
        f"/api/v1/wishlist/products/{product.id}",
    )

    assert response.status_code == 401


def test_remove_product_from_wishlist(client, test_db):
    headers = get_auth_headers(client)

    product = test_db.scalar(
        select(Product).where(
            Product.slug == "nexora-pro-laptop",
        )
    )

    assert product is not None

    add_response = client.post(
        f"/api/v1/wishlist/products/{product.id}",
        headers=headers,
    )

    assert add_response.status_code == 201

    delete_response = client.delete(
        f"/api/v1/wishlist/products/{product.id}",
        headers=headers,
    )

    assert delete_response.status_code == 204

    wishlist_item = test_db.scalar(
        select(WishlistItem).where(
            WishlistItem.product_id == product.id,
        )
    )

    assert wishlist_item is None


def test_remove_nonexistent_wishlist_item_returns_not_found(client):
    headers = get_auth_headers(client)

    product_id = uuid.uuid4()

    response = client.delete(
        f"/api/v1/wishlist/products/{product_id}",
        headers=headers,
    )

    assert response.status_code == 404


def test_wishlist_is_user_specific(client, test_db):
    first_user_headers = get_auth_headers(client)

    second_user_headers = get_auth_headers(
        client,
        email="other.test@nexora.com",
    )

    product = test_db.scalar(
        select(Product).where(
            Product.slug == "nexora-pro-laptop",
        )
    )

    assert product is not None

    first_response = client.post(
        f"/api/v1/wishlist/products/{product.id}",
        headers=first_user_headers,
    )

    assert first_response.status_code == 201

    second_user_response = client.get(
        "/api/v1/wishlist",
        headers=second_user_headers,
    )

    assert second_user_response.status_code == 200
    assert second_user_response.json() == []


def test_remove_wishlist_item_is_user_specific(client, test_db):
    first_user_headers = get_auth_headers(client)

    second_user_headers = get_auth_headers(
        client,
        email="other.test@nexora.com",
    )

    product = test_db.scalar(
        select(Product).where(
            Product.slug == "nexora-pro-laptop",
        )
    )

    assert product is not None

    add_response = client.post(
        f"/api/v1/wishlist/products/{product.id}",
        headers=first_user_headers,
    )

    assert add_response.status_code == 201

    other_user_delete = client.delete(
        f"/api/v1/wishlist/products/{product.id}",
        headers=second_user_headers,
    )

    assert other_user_delete.status_code == 404

    wishlist_item = test_db.scalar(
        select(WishlistItem).where(
            WishlistItem.product_id == product.id,
        )
    )

    assert wishlist_item is not None