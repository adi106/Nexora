from sqlalchemy import select

from backend.app.models import Product, Review


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

def login_as_other_user(client):
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "other.test@nexora.com",
            "password": "TestPassword123!",
        },
    )

    assert response.status_code == 200

    return response.json()["access_token"]


def test_create_review_requires_authentication(client, test_db):
    product = test_db.query(Product).first()
    assert product is not None

    response = client.post(
        f"/api/v1/reviews/products/{product.id}",
        json={
            "rating": 5,
            "comment": "Excellent product!",
        },
    )

    assert response.status_code in (401, 403)


def test_create_review(client, test_db):
    product = test_db.query(Product).first()
    assert product is not None

    token = login(client)

    response = client.post(
        f"/api/v1/reviews/products/{product.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "rating": 5,
            "comment": "Excellent product!",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["product_id"] == str(product.id)
    assert data["rating"] == 5
    assert data["comment"] == "Excellent product!"

    review = test_db.scalar(
        select(Review).where(Review.id == data["id"])
    )

    assert review is not None
    assert review.product_id == product.id

def test_create_duplicate_review_returns_conflict(client, test_db):
    product = test_db.query(Product).first()
    assert product is not None

    token = login(client)
    headers = {"Authorization": f"Bearer {token}"}

    first_response = client.post(
        f"/api/v1/reviews/products/{product.id}",
        headers=headers,
        json={
            "rating": 5,
            "comment": "Excellent product!",
        },
    )

    assert first_response.status_code == 201

    second_response = client.post(
        f"/api/v1/reviews/products/{product.id}",
        headers=headers,
        json={
            "rating": 4,
            "comment": "Trying to review again.",
        },
    )

    assert second_response.status_code == 409
    assert second_response.json()["detail"] == (
        "You have already reviewed this product"
    )

def test_list_product_reviews(client, test_db):
    product = test_db.query(Product).first()
    assert product is not None

    token = login(client)

    create_response = client.post(
        f"/api/v1/reviews/products/{product.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "rating": 4,
            "comment": "Good product.",
        },
    )

    assert create_response.status_code == 201

    response = client.get(
        f"/api/v1/reviews/products/{product.id}"
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["product_id"] == str(product.id)
    assert data[0]["rating"] == 4
    assert data[0]["comment"] == "Good product."

def test_update_own_review(client, test_db):
    product = test_db.query(Product).first()
    assert product is not None

    token = login(client)
    headers = {"Authorization": f"Bearer {token}"}

    create_response = client.post(
        f"/api/v1/reviews/products/{product.id}",
        headers=headers,
        json={
            "rating": 3,
            "comment": "It was okay.",
        },
    )

    assert create_response.status_code == 201

    review_id = create_response.json()["id"]

    update_response = client.put(
        f"/api/v1/reviews/{review_id}",
        headers=headers,
        json={
            "rating": 5,
            "comment": "Actually, excellent product!",
        },
    )

    assert update_response.status_code == 200

    data = update_response.json()

    assert data["id"] == review_id
    assert data["rating"] == 5
    assert data["comment"] == "Actually, excellent product!"

def test_cannot_update_another_users_review(client, test_db):
    product = test_db.query(Product).first()
    assert product is not None

    owner_token = login(client)

    create_response = client.post(
        f"/api/v1/reviews/products/{product.id}",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={
            "rating": 5,
            "comment": "Owner review.",
        },
    )

    assert create_response.status_code == 201

    review_id = create_response.json()["id"]

    other_token = login_as_other_user(client)

    update_response = client.put(
        f"/api/v1/reviews/{review_id}",
        headers={"Authorization": f"Bearer {other_token}"},
        json={
            "rating": 1,
            "comment": "Unauthorized update.",
        },
    )

    assert update_response.status_code == 404
    assert update_response.json()["detail"] == "Review not found"

def test_cannot_delete_another_users_review(client, test_db):
    product = test_db.query(Product).first()
    assert product is not None

    owner_token = login(client)

    create_response = client.post(
        f"/api/v1/reviews/products/{product.id}",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={
            "rating": 5,
            "comment": "Owner review.",
        },
    )

    assert create_response.status_code == 201

    review_id = create_response.json()["id"]

    other_token = login_as_other_user(client)

    delete_response = client.delete(
        f"/api/v1/reviews/{review_id}",
        headers={"Authorization": f"Bearer {other_token}"},
    )

    assert delete_response.status_code == 404
    assert delete_response.json()["detail"] == "Review not found"

def test_delete_own_review(client, test_db):
    product = test_db.query(Product).first()
    assert product is not None

    token = login(client)
    headers = {"Authorization": f"Bearer {token}"}

    create_response = client.post(
        f"/api/v1/reviews/products/{product.id}",
        headers=headers,
        json={
            "rating": 5,
            "comment": "Review to delete.",
        },
    )

    assert create_response.status_code == 201

    review_id = create_response.json()["id"]

    delete_response = client.delete(
        f"/api/v1/reviews/{review_id}",
        headers=headers,
    )

    assert delete_response.status_code == 204

    deleted_review = test_db.scalar(
        select(Review).where(Review.id == review_id)
    )

    assert deleted_review is None

def test_create_review_rejects_invalid_rating(client, test_db):
    product = test_db.query(Product).first()
    assert product is not None

    token = login(client)
    headers = {"Authorization": f"Bearer {token}"}

    for rating in (0, 6):
        response = client.post(
            f"/api/v1/reviews/products/{product.id}",
            headers=headers,
            json={
                "rating": rating,
                "comment": "Invalid rating.",
            },
        )

        assert response.status_code == 422

def test_create_review_for_missing_product_returns_not_found(client):
    token = login(client)

    response = client.post(
        "/api/v1/reviews/products/00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "rating": 5,
            "comment": "This product does not exist.",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Product not found"

def test_get_product_rating(client, test_db):
    product = test_db.query(Product).first()
    assert product is not None

    owner_token = login(client)
    other_token = login_as_other_user(client)

    first_response = client.post(
        f"/api/v1/reviews/products/{product.id}",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={
            "rating": 5,
            "comment": "Five stars.",
        },
    )

    assert first_response.status_code == 201

    second_response = client.post(
        f"/api/v1/reviews/products/{product.id}",
        headers={"Authorization": f"Bearer {other_token}"},
        json={
            "rating": 3,
            "comment": "Three stars.",
        },
    )

    assert second_response.status_code == 201

    response = client.get(
        f"/api/v1/reviews/products/{product.id}/rating"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["average_rating"] == 4.0
    assert data["review_count"] == 2