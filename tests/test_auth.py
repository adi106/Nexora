def test_login_success(client):
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "secure.test@nexora.com",
            "password": "TestPassword123!",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client):
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "secure.test@nexora.com",
            "password": "WrongPassword123!",
        },
    )

    assert response.status_code == 401