from sqlalchemy import select

from backend.app.models import Product


def test_categories_list_carries_cache_header(client):
    response = client.get("/api/v1/categories")
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "public, max-age=300"


def test_products_list_carries_cache_header(client):
    response = client.get("/api/v1/products")
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "public, max-age=15"


def test_product_detail_carries_cache_header(client, test_db):
    product = test_db.scalar(select(Product).where(Product.slug == "nexora-pro-laptop"))

    response = client.get(f"/api/v1/products/{product.id}")

    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "public, max-age=15"
