from sqlalchemy import select

from backend.app.models import Category


TEST_CATEGORY_SLUG = "laptops"


def get_test_category(test_db):
    category = test_db.scalar(
        select(Category).where(
            Category.slug == TEST_CATEGORY_SLUG
        )
    )

    assert category is not None

    return category

def login_as_test_admin(client):
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "test.admin@nexora.local",
            "password": "TestPassword123!",
        },
    )

    assert response.status_code == 200

    return response.json()["access_token"]

def login_as_test_admin(client):
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "test.admin@nexora.local",
            "password": "TestPassword123!",
        },
    )

    assert response.status_code == 200

    return response.json()["access_token"]



def test_list_categories(client):
    response = client.get(
        "/api/v1/categories"
    )

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, list)
    assert len(data) >= 1


def test_list_categories_excludes_inactive_category(client, test_db):
    category = get_test_category(test_db)

    category.is_active = False
    test_db.commit()

    response = client.get(
        "/api/v1/categories"
    )

    assert response.status_code == 200

    data = response.json()

    category_ids = {item["id"] for item in data}

    assert category.id not in category_ids


def test_get_category(client, test_db):
    category = get_test_category(test_db)

    response = client.get(
        f"/api/v1/categories/{category.id}"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == category.id
    assert data["name"] == "Laptops"
    assert data["slug"] == TEST_CATEGORY_SLUG


def test_get_inactive_category_returns_not_found(client, test_db):
    category = get_test_category(test_db)

    category.is_active = False
    test_db.commit()

    response = client.get(
        f"/api/v1/categories/{category.id}"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Category not found"


def test_get_category_not_found(client):
    response = client.get(
        "/api/v1/categories/999999"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Category not found"


def test_admin_can_update_category_status(client, test_db):
    category = get_test_category(test_db)
    token = login_as_test_admin(client)

    response = client.patch(
        f"/api/v1/categories/{category.id}",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "is_active": False,
        },
    )

    assert response.status_code == 200
    assert response.json()["id"] == category.id
    assert response.json()["is_active"] is False

    test_db.expire_all()

    updated_category = test_db.get(Category, category.id)

    assert updated_category is not None
    assert updated_category.is_active is False

    response = client.patch(
        f"/api/v1/categories/{category.id}",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "is_active": True,
        },
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is True


def test_customer_cannot_update_category_status(client, test_db):
    category = get_test_category(test_db)

    token_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "secure.test@nexora.com",
            "password": "TestPassword123!",
        },
    )

    assert token_response.status_code == 200

    token = token_response.json()["access_token"]

    response = client.patch(
        f"/api/v1/categories/{category.id}",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "is_active": False,
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions"

    test_db.expire_all()

    unchanged_category = test_db.get(Category, category.id)

    assert unchanged_category is not None
    assert unchanged_category.is_active is True


def test_seller_cannot_update_category_status(client, test_db):
    category = get_test_category(test_db)

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
        f"/api/v1/categories/{category.id}",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "is_active": False,
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions"

    test_db.expire_all()

    unchanged_category = test_db.get(Category, category.id)

    assert unchanged_category is not None
    assert unchanged_category.is_active is True