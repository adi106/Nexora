from uuid import uuid4

from sqlalchemy import select

from backend.app.models.product import Product
from backend.app.models.product_interaction import ProductInteraction
from backend.app.models.user import User


def get_auth_headers(client, email):
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


def test_create_product_view_interaction(client, test_db):
    user = test_db.scalar(
        select(User).where(
            User.email == "secure.test@nexora.com"
        )
    )

    assert user is not None

    product = test_db.execute(
        select(Product).where(
            Product.slug == "nexora-pro-laptop"
        )
    ).scalar_one()

    headers = get_auth_headers(
        client,
        "secure.test@nexora.com",
    )

    response = client.post(
        "/api/v1/recommendations/interactions",
        json={
            "product_id": str(product.id),
            "interaction_type": "view",
        },
        headers=headers,
    )

    assert response.status_code == 201

    data = response.json()

    assert data["user_id"] == str(user.id)
    assert data["product_id"] == str(product.id)
    assert data["interaction_type"] == "view"

    interaction = test_db.get(
        ProductInteraction,
        data["id"],
    )

    assert interaction is not None
    assert interaction.user_id == user.id
    assert interaction.product_id == product.id


def test_create_product_interaction_requires_authentication(
    client,
    test_db,
):
    product = test_db.execute(
        select(Product).where(
            Product.slug == "nexora-pro-laptop"
        )
    ).scalar_one()

    response = client.post(
        "/api/v1/recommendations/interactions",
        json={
            "product_id": str(product.id),
            "interaction_type": "view",
        },
    )

    assert response.status_code == 401


def test_create_product_interaction_rejects_unknown_product(
    client,
):
    headers = get_auth_headers(
        client,
        "secure.test@nexora.com",
    )

    response = client.post(
        "/api/v1/recommendations/interactions",
        json={
            "product_id": str(uuid4()),
            "interaction_type": "view",
        },
        headers=headers,
    )

    assert response.status_code == 404

def test_get_product_recommendations_requires_authentication(
    client,
):
    response = client.get(
        "/api/v1/recommendations",
    )

    assert response.status_code == 401


def test_get_product_recommendations_respects_limit(
    client,
):
    headers = get_auth_headers(
        client,
        "secure.test@nexora.com",
    )

    response = client.get(
        "/api/v1/recommendations?limit=2",
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, list)
    assert len(data) <= 2

    for product in data:
        assert "id" in product
        assert "name" in product
        assert "slug" in product
        assert "base_price" in product
        assert "seller_id" in product
        assert "category_id" in product
        assert "is_active" in product