from sqlalchemy import select

from backend.app.models import Product


TEST_PRODUCT_SLUG = "nexora-pro-laptop"


def get_test_product(test_db):
    product = test_db.scalar(
        select(Product).where(
            Product.slug == TEST_PRODUCT_SLUG
        )
    )

    assert product is not None

    return product


def test_list_products(client):
    response = client.get(
        "/api/v1/products"
    )

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, list)
    assert len(data) >= 1


def test_list_products_excludes_inactive_product(client, test_db):
    product = get_test_product(test_db)

    product.is_active = False
    test_db.commit()

    response = client.get(
        "/api/v1/products"
    )

    assert response.status_code == 200

    data = response.json()

    product_ids = {item["id"] for item in data}

    assert str(product.id) not in product_ids


def test_get_product(client, test_db):
    product = get_test_product(test_db)

    response = client.get(
        f"/api/v1/products/{product.id}"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == str(product.id)
    assert data["name"] == "NEXORA Pro Laptop"
    assert data["seller_id"] == product.seller_id


def test_get_inactive_product_returns_not_found(client, test_db):
    product = get_test_product(test_db)

    product.is_active = False
    test_db.commit()

    response = client.get(
        f"/api/v1/products/{product.id}"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Product not found"


def test_get_product_not_found(client):
    product_id = "00000000-0000-0000-0000-000000000000"

    response = client.get(
        f"/api/v1/products/{product_id}"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Product not found"