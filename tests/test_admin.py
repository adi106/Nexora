import uuid

from sqlalchemy import select

from backend.app.models import Product, User


TEST_PASSWORD = "TestPassword123!"
ADMIN_EMAIL = "test.admin@nexora.local"
BUYER_EMAIL = "secure.test@nexora.com"
SELLER_EMAIL = "test.seller@nexora.local"


def login(client, email):
    response = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": TEST_PASSWORD},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_admin_stats_requires_admin_role(client):
    buyer_token = login(client, BUYER_EMAIL)

    response = client.get(
        "/api/v1/admin/stats",
        headers={"Authorization": f"Bearer {buyer_token}"},
    )

    assert response.status_code == 403


def test_admin_stats_requires_authentication(client):
    response = client.get("/api/v1/admin/stats")
    assert response.status_code == 401


def test_admin_stats_returns_platform_totals(client, test_db):
    token = login(client, ADMIN_EMAIL)

    response = client.get("/api/v1/admin/stats", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    data = response.json()
    assert data["user_count"] >= 1
    assert data["seller_count"] >= 1
    assert data["product_count"] >= 1


def test_admin_list_users_search(client, test_db):
    token = login(client, ADMIN_EMAIL)

    response = client.get(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {token}"},
        params={"search": "secure.test"},
    )

    assert response.status_code == 200
    data = response.json()
    assert any(item["email"] == BUYER_EMAIL for item in data["items"])


def test_admin_cannot_deactivate_own_account(client, test_db):
    token = login(client, ADMIN_EMAIL)
    admin = test_db.scalar(select(User).where(User.email == ADMIN_EMAIL))

    response = client.patch(
        f"/api/v1/admin/users/{admin.id}/status",
        headers={"Authorization": f"Bearer {token}"},
        json={"is_active": False},
    )

    assert response.status_code == 400


def test_admin_can_deactivate_and_reactivate_another_user(client, test_db):
    token = login(client, ADMIN_EMAIL)

    email = f"deactivate.{uuid.uuid4().hex[:8]}@nexora.com"
    created = client.post(
        "/api/v1/users",
        json={"email": email, "password": TEST_PASSWORD, "first_name": "D", "last_name": "User"},
    )
    assert created.status_code == 201
    user_id = created.json()["id"]

    deactivate = client.patch(
        f"/api/v1/admin/users/{user_id}/status",
        headers={"Authorization": f"Bearer {token}"},
        json={"is_active": False},
    )
    assert deactivate.status_code == 200
    assert deactivate.json()["is_active"] is False

    login_attempt = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": TEST_PASSWORD},
    )
    assert login_attempt.status_code == 403

    reactivate = client.patch(
        f"/api/v1/admin/users/{user_id}/status",
        headers={"Authorization": f"Bearer {token}"},
        json={"is_active": True},
    )
    assert reactivate.status_code == 200
    assert reactivate.json()["is_active"] is True


def test_admin_list_sellers(client, test_db):
    token = login(client, ADMIN_EMAIL)

    response = client.get("/api/v1/admin/sellers", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    data = response.json()
    assert any(item["store_slug"] == "nexora-test-store" for item in data["items"])


def test_admin_can_deactivate_seller(client, test_db):
    token = login(client, ADMIN_EMAIL)

    sellers = client.get("/api/v1/admin/sellers", headers={"Authorization": f"Bearer {token}"})
    seller = next(s for s in sellers.json()["items"] if s["store_slug"] == "nexora-test-store")

    response = client.patch(
        f"/api/v1/admin/sellers/{seller['id']}/status",
        headers={"Authorization": f"Bearer {token}"},
        json={"is_active": True},
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is True


def test_admin_list_products_and_force_deactivate(client, test_db):
    token = login(client, ADMIN_EMAIL)
    product = test_db.scalar(select(Product).where(Product.slug == "nexora-pro-laptop"))

    listing = client.get("/api/v1/admin/products", headers={"Authorization": f"Bearer {token}"})
    assert listing.status_code == 200
    assert any(item["id"] == str(product.id) for item in listing.json()["items"])

    deactivated = client.patch(
        f"/api/v1/admin/products/{product.id}/status",
        headers={"Authorization": f"Bearer {token}"},
        json={"is_active": False},
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["is_active"] is False

    reactivated = client.patch(
        f"/api/v1/admin/products/{product.id}/status",
        headers={"Authorization": f"Bearer {token}"},
        json={"is_active": True},
    )
    assert reactivated.status_code == 200
    assert reactivated.json()["is_active"] is True


def test_admin_list_categories_includes_inactive(client, test_db):
    token = login(client, ADMIN_EMAIL)
    unique = uuid.uuid4().hex[:8]

    created = client.post(
        "/api/v1/categories",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": f"Cat {unique}", "slug": f"cat-{unique}", "is_active": True},
    )
    assert created.status_code == 201
    category_id = created.json()["id"]

    deactivated = client.patch(
        f"/api/v1/categories/{category_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"is_active": False},
    )
    assert deactivated.status_code == 200

    listing = client.get("/api/v1/admin/categories", headers={"Authorization": f"Bearer {token}"})
    assert listing.status_code == 200
    assert any(item["id"] == category_id and item["is_active"] is False for item in listing.json())


def test_admin_list_orders(client, test_db):
    token = login(client, ADMIN_EMAIL)

    response = client.get("/api/v1/admin/orders", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_non_admin_cannot_access_admin_endpoints(client, test_db):
    seller_token = login(client, SELLER_EMAIL)

    for path in ["/api/v1/admin/users", "/api/v1/admin/sellers", "/api/v1/admin/products", "/api/v1/admin/orders"]:
        response = client.get(path, headers={"Authorization": f"Bearer {seller_token}"})
        assert response.status_code == 403, path
