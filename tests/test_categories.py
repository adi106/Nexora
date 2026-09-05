def test_list_categories(client):
    response = client.get("/api/v1/categories")

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, list)
    assert len(data) >= 1

def test_get_category(client):
    response = client.get("/api/v1/categories/10")

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == 10
    assert data["name"] == "Laptops"
    assert data["slug"] == "laptops"

def test_get_category_not_found(client):
    response = client.get("/api/v1/categories/999999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Category not found"