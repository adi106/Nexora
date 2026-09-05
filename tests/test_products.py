def test_list_products(client):
    response = client.get("/api/v1/products")

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, list)
    assert len(data) >= 1


def test_get_product(client):
    product_id = "859e5c66-53d4-4f35-993d-fa6733dc5d66"

    response = client.get(
        f"/api/v1/products/{product_id}"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == product_id
    assert data["name"] == "NEXORA Gaming Laptop"
    assert data["seller_id"] == 2

def test_get_product_not_found(client):
    product_id = "00000000-0000-0000-0000-000000000000"

    response = client.get(
        f"/api/v1/products/{product_id}"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Product not found"