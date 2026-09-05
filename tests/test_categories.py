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


def test_list_categories(client):
    response = client.get(
        "/api/v1/categories"
    )

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, list)
    assert len(data) >= 1


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


def test_get_category_not_found(client):
    response = client.get(
        "/api/v1/categories/999999"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Category not found"