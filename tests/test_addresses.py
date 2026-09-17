import uuid

from sqlalchemy import select

from backend.app.models import User


TEST_EMAIL = "secure.test@nexora.com"
TEST_PASSWORD = "TestPassword123!"


def login(client, email):
    response = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": TEST_PASSWORD},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def register_and_login(client):
    email = f"addr.{uuid.uuid4().hex[:10]}@nexora.com"
    created = client.post(
        "/api/v1/users",
        json={
            "email": email,
            "password": TEST_PASSWORD,
            "first_name": "Addr",
            "last_name": "Tester",
        },
    )
    assert created.status_code == 201
    return login(client, email)


def get_test_user(test_db, email=TEST_EMAIL):
    user = test_db.scalar(select(User).where(User.email == email))
    assert user is not None
    return user


def test_list_addresses_requires_authentication(client):
    response = client.get("/api/v1/addresses")
    assert response.status_code == 401


def test_list_addresses_returns_only_own_addresses(client, test_db):
    token = login(client, TEST_EMAIL)

    response = client.get(
        "/api/v1/addresses",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    user = get_test_user(test_db)
    assert all(item["user_id"] == str(user.id) for item in data)
    assert len(data) >= 1


def test_create_address_becomes_default_when_first(client, test_db):
    token = register_and_login(client)

    response = client.post(
        "/api/v1/addresses",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "address_line1": "1 Test Way",
            "city": "Testville",
            "postal_code": "00000",
            "country_code": "us",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["is_default"] is True
    assert data["country_code"] == "US"


def test_create_second_default_unsets_previous_default(client, test_db):
    token = register_and_login(client)

    first = client.post(
        "/api/v1/addresses",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "address_line1": "First St",
            "city": "City",
            "postal_code": "11111",
            "country_code": "US",
            "is_default": True,
        },
    )
    assert first.status_code == 201
    first_id = first.json()["id"]

    second = client.post(
        "/api/v1/addresses",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "address_line1": "Second St",
            "city": "City",
            "postal_code": "22222",
            "country_code": "US",
            "is_default": True,
        },
    )
    assert second.status_code == 201
    assert second.json()["is_default"] is True

    refreshed_first = client.get(
        f"/api/v1/addresses/{first_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert refreshed_first.json()["is_default"] is False


def test_get_address_not_owned_returns_404(client, test_db):
    owner_token = register_and_login(client)
    other_token = register_and_login(client)

    created = client.post(
        "/api/v1/addresses",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={
            "address_line1": "Private Rd",
            "city": "City",
            "postal_code": "33333",
            "country_code": "US",
        },
    )
    assert created.status_code == 201
    address_id = created.json()["id"]

    response = client.get(
        f"/api/v1/addresses/{address_id}",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert response.status_code == 404


def test_update_address(client, test_db):
    token = register_and_login(client)

    created = client.post(
        "/api/v1/addresses",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "address_line1": "Old Line",
            "city": "City",
            "postal_code": "44444",
            "country_code": "US",
        },
    )
    address_id = created.json()["id"]

    updated = client.put(
        f"/api/v1/addresses/{address_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"address_line1": "New Line"},
    )

    assert updated.status_code == 200
    assert updated.json()["address_line1"] == "New Line"


def test_delete_default_address_promotes_another(client, test_db):
    token = register_and_login(client)

    first = client.post(
        "/api/v1/addresses",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "address_line1": "Keep St",
            "city": "City",
            "postal_code": "55555",
            "country_code": "US",
        },
    )
    first_id = first.json()["id"]

    second = client.post(
        "/api/v1/addresses",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "address_line1": "Delete St",
            "city": "City",
            "postal_code": "66666",
            "country_code": "US",
            "is_default": True,
        },
    )
    second_id = second.json()["id"]

    delete_response = client.delete(
        f"/api/v1/addresses/{second_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert delete_response.status_code == 204

    remaining = client.get(
        "/api/v1/addresses",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert any(item["is_default"] for item in remaining.json())
    assert first_id in [item["id"] for item in remaining.json()]
