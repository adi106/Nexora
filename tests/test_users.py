def test_get_current_user(client):
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
        "/api/v1/users/me",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["email"] == "secure.test@nexora.com"
    assert data["is_active"] is True


def test_get_current_user_unauthenticated(client):
    response = client.get("/api/v1/users/me")

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"