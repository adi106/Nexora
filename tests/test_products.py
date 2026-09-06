from sqlalchemy import select

from backend.app.core.security import hash_password

from backend.app.models import Category, Product, Role, Seller, User, UserRole

from backend.app.models.product_variant import ProductVariant

from backend.app.models.inventory import Inventory

from decimal import Decimal
from uuid import UUID

import uuid


TEST_PRODUCT_SLUG = "nexora-pro-laptop"


def get_test_product(test_db):
    product = test_db.scalar(
        select(Product).where(
            Product.slug == TEST_PRODUCT_SLUG
        )
    )

    assert product is not None

    return product


def login_as_test_seller(client):
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "test.seller@nexora.local",
            "password": "TestPassword123!",
        },
    )

    assert response.status_code == 200

    return response.json()["access_token"]


def test_list_products(client):
    response = client.get(
        "/api/v1/products"
    )

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, dict)
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data

    assert isinstance(data["items"], list)
    assert data["page"] == 1
    assert data["page_size"] == 20
    assert data["total"] >= len(data["items"])
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

    product_ids = {item["id"] for item in data["items"]}

    assert str(product.id) not in product_ids

def test_list_products_excludes_product_with_inactive_category(client, test_db):
    product = get_test_product(test_db)

    category = test_db.scalar(
        select(Category).where(
            Category.id == product.category_id
        )
    )

    assert category is not None

    category.is_active = False
    test_db.commit()

    response = client.get(
        "/api/v1/products"
    )

    assert response.status_code == 200

    data = response.json()

    product_ids = {item["id"] for item in data["items"]}

    assert str(product.id) not in product_ids



def test_get_product_returns_not_found_with_inactive_category(client, test_db):
    product = get_test_product(test_db)

    category = test_db.scalar(
        select(Category).where(
            Category.id == product.category_id
        )
    )

    assert category is not None

    category.is_active = False
    test_db.commit()

    response = client.get(
        f"/api/v1/products/{product.id}"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Product not found"



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


def test_update_product_status_requires_authentication(client, test_db):
    product = get_test_product(test_db)

    response = client.patch(
        f"/api/v1/products/{product.id}",
        json={
            "is_active": False,
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_seller_can_update_own_product_status(client, test_db):
    product = get_test_product(test_db)
    token = login_as_test_seller(client)

    response = client.patch(
        f"/api/v1/products/{product.id}",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "is_active": False,
        },
    )

    assert response.status_code == 200
    assert response.json()["id"] == str(product.id)
    assert response.json()["is_active"] is False

    test_db.expire_all()

    updated_product = test_db.get(Product, product.id)
    assert updated_product is not None
    assert updated_product.is_active is False

    response = client.patch(
        f"/api/v1/products/{product.id}",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "is_active": True,
        },
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is True

def test_seller_cannot_update_another_sellers_product(client, test_db):
    product = get_test_product(test_db)

    seller_role = test_db.scalar(
        select(Role).where(
            Role.name == "seller"
        )
    )

    assert seller_role is not None

    other_user = test_db.scalar(
        select(User).where(
            User.email == "other.test.seller@nexora.local"
        )
    )

    if other_user is None:
        other_user = User(
            email="other.test.seller@nexora.local",
            password_hash=hash_password("TestPassword123!"),
            first_name="Other",
            last_name="Seller",
        )
        test_db.add(other_user)
        test_db.flush()

    existing_role = test_db.scalar(
        select(UserRole).where(
            UserRole.user_id == other_user.id,
            UserRole.role_id == seller_role.id,
        )
    )

    if existing_role is None:
        test_db.add(
            UserRole(
                user_id=other_user.id,
                role_id=seller_role.id,
            )
        )

    other_seller = test_db.scalar(
        select(Seller).where(
            Seller.user_id == other_user.id
        )
    )

    if other_seller is None:
        other_seller = Seller(
            user_id=other_user.id,
            store_name="Other Test Store",
            store_slug="other-test-store",
            description="Second test seller",
        )
        test_db.add(other_seller)

    test_db.commit()

    token_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "other.test.seller@nexora.local",
            "password": "TestPassword123!",
        },
    )

    assert token_response.status_code == 200

    token = token_response.json()["access_token"]

    response = client.patch(
        f"/api/v1/products/{product.id}",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "is_active": False,
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "You do not have permission to modify this product"
    )

    test_db.expire_all()

    unchanged_product = test_db.get(Product, product.id)

    assert unchanged_product is not None
    assert unchanged_product.is_active is True

    # Log in as the second seller.
    # We need a real password hash so authentication succeeds.


def test_customer_cannot_update_product_status(client, test_db):
    product = get_test_product(test_db)

    token_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "secure.test@nexora.com",
            "password": "TestPassword123!",
        },
    )

    assert token_response.status_code == 200

    token = token_response.json()["access_token"]

    response = client.patch(
        f"/api/v1/products/{product.id}",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "is_active": False,
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions"

    test_db.expire_all()

    unchanged_product = test_db.get(Product, product.id)

    assert unchanged_product is not None
    assert unchanged_product.is_active is True


def test_seller_can_update_own_product_details(client, test_db):
    product = get_test_product(test_db)
    token = login_as_test_seller(client)

    response = client.put(
        f"/api/v1/products/{product.id}/details",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "name": "Updated NEXORA Pro Laptop",
            "slug": "updated-nexora-pro-laptop-details-test",
            "description": "Updated product description",
            "base_price": "1499.99",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["name"] == "Updated NEXORA Pro Laptop"
    assert data["slug"] == "updated-nexora-pro-laptop-details-test"
    assert data["description"] == "Updated product description"
    assert data["base_price"] == "1499.99"
    assert data["is_active"] is True

    test_db.refresh(product)

    assert product.name == "Updated NEXORA Pro Laptop"
    assert product.slug == "updated-nexora-pro-laptop-details-test"
    assert product.description == "Updated product description"
    product.name = "NEXORA Pro Laptop"
    product.slug = "nexora-pro-laptop"
    product.description = "Test product"
    product.base_price = 999.99

    test_db.commit()


def test_seller_cannot_update_another_sellers_product_details(client, test_db):
    product = get_test_product(test_db)

    seller_role = test_db.scalar(
        select(Role).where(Role.name == "seller")
    )

    assert seller_role is not None

    other_user = test_db.scalar(
        select(User).where(
            User.email == "other.test.seller@nexora.local"
        )
    )

    if other_user is None:
        other_user = User(
            email="other.test.seller@nexora.local",
            password_hash=hash_password("TestPassword123!"),
            first_name="Other",
            last_name="Seller",
        )
        test_db.add(other_user)
        test_db.flush()

    existing_role = test_db.scalar(
        select(UserRole).where(
            UserRole.user_id == other_user.id,
            UserRole.role_id == seller_role.id,
        )
    )

    if existing_role is None:
        test_db.add(
            UserRole(
                user_id=other_user.id,
                role_id=seller_role.id,
            )
        )

    other_seller = test_db.scalar(
        select(Seller).where(
            Seller.user_id == other_user.id
        )
    )

    if other_seller is None:
        other_seller = Seller(
            user_id=other_user.id,
            store_name="Other Test Store",
            store_slug="other-test-store",
            description="Second test seller",
        )
        test_db.add(other_seller)

    test_db.commit()

    token_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "other.test.seller@nexora.local",
            "password": "TestPassword123!",
        },
    )

    assert token_response.status_code == 200

    token = token_response.json()["access_token"]

    response = client.put(
        f"/api/v1/products/{product.id}/details",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "name": "Unauthorized Product Change",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "You do not have permission to modify this product"
    )

def test_update_product_details_requires_authentication(client, test_db):
    product = get_test_product(test_db)

    response = client.put(
        f"/api/v1/products/{product.id}/details",
        json={
            "name": "Unauthorized Update",
        },
    )

    assert response.status_code == 401

def test_update_product_details_rejects_duplicate_slug(client, test_db):
    product = get_test_product(test_db)
    token = login_as_test_seller(client)

    other_product = test_db.scalar(
        select(Product).where(
            Product.slug == "other-test-product"
        )
    )

    if other_product is None:
        other_product = Product(
            seller_id=product.seller_id,
            category_id=product.category_id,
            name="Another Test Product",
            slug="other-test-product",
            description="Another product",
            base_price=500.00,
        )
        test_db.add(other_product)
        test_db.commit()

    response = client.put(
        f"/api/v1/products/{product.id}/details",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "slug": "other-test-product",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Product slug already exists"


def test_update_product_details_rejects_inactive_category(client, test_db):
    product = get_test_product(test_db)
    token = login_as_test_seller(client)

    category = test_db.scalar(
        select(Category).where(Category.id == product.category_id)
    )

    assert category is not None

    category.is_active = False
    test_db.commit()

    response = client.put(
        f"/api/v1/products/{product.id}/details",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "category_id": category.id,
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Category is not active"

def test_seller_can_create_product_variant(client, test_db):
    product = get_test_product(test_db)
    token = login_as_test_seller(client)

    response = client.post(
        f"/api/v1/products/{product.id}/variants",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "sku": "NEXORA-TEST-VARIANT-HAPPY-PATH",
            "price": "1299.99",
            "attributes": {
                "ram": "32GB",
                "storage": "1TB",
            },
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["product_id"] == str(product.id)
    assert data["sku"] == "NEXORA-TEST-VARIANT-HAPPY-PATH"
    assert data["price"] == "1299.99"
    assert data["attributes"] == {
        "ram": "32GB",
        "storage": "1TB",
    }
    inventory = test_db.scalar(
    select(Inventory).where(
        Inventory.variant_id == UUID(data["id"])
    )
)

    assert inventory is not None
    assert inventory.quantity == 0
    assert inventory.reserved_quantity == 0
    assert inventory.reorder_level == 5
    assert inventory.is_active is True

def test_seller_cannot_create_variant_for_another_sellers_product(
    client,
    test_db,
):
    product = get_test_product(test_db)

    seller_role = test_db.scalar(
        select(Role).where(Role.name == "seller")
    )

    assert seller_role is not None

    other_user = test_db.scalar(
        select(User).where(
            User.email == "other.test.seller@nexora.local"
        )
    )

    assert other_user is not None

    other_seller = test_db.scalar(
        select(Seller).where(
            Seller.user_id == other_user.id
        )
    )

    assert other_seller is not None

    token_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "other.test.seller@nexora.local",
            "password": "TestPassword123!",
        },
    )

    assert token_response.status_code == 200

    token = token_response.json()["access_token"]

    response = client.post(
        f"/api/v1/products/{product.id}/variants",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "sku": "NEXORA-UNAUTHORIZED-VARIANT-001",
            "price": "999.99",
            "attributes": {
                "ram": "16GB",
            },
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "You do not have permission to modify this product"

   )


def test_create_product_variant_requires_authentication(client, test_db):
    product = get_test_product(test_db)

    response = client.post(
        f"/api/v1/products/{product.id}/variants",
        json={
            "sku": "NEXORA-UNAUTH-VARIANT-001",
            "price": "999.99",
            "attributes": {
                "ram": "16GB",
            },
        },
    )

    assert response.status_code == 401


def test_create_product_variant_rejects_duplicate_sku(client, test_db):
    product = get_test_product(test_db)
    token = login_as_test_seller(client)

    existing_variant = test_db.scalar(
        select(ProductVariant).where(
            ProductVariant.sku == "NEXORA-PRO-16-512"
        )
    )

    assert existing_variant is not None
    assert existing_variant.product_id == product.id

    response = client.post(
        f"/api/v1/products/{product.id}/variants",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "sku": existing_variant.sku,
            "price": 1499.99,
            "attributes": {
                "ram": "32GB",
                "storage": "1TB",
            },
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Product variant SKU already exists"


def test_create_product_variant_rejects_nonexistent_product(
    client,
    test_db,
):
    token = login_as_test_seller(client)

    nonexistent_product_id = uuid.uuid4()

    response = client.post(
        f"/api/v1/products/{nonexistent_product_id}/variants",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "sku": "NEXORA-NONEXISTENT-PRODUCT-001",
            "price": "999.99",
            "attributes": {
                "ram": "16GB",
            },
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Product not found"


def test_create_product_variant_rejects_inactive_product(client, test_db):
    product = get_test_product(test_db)
    token = login_as_test_seller(client)

    product.is_active = False
    test_db.commit()

    response = client.post(
        f"/api/v1/products/{product.id}/variants",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "sku": "NEXORA-INACTIVE-PRODUCT-001",
            "price": "999.99",
            "attributes": {
                "ram": "16GB",
            },
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Product is not active"


def test_create_product_variant_rejects_inactive_category(client, test_db):
    product = get_test_product(test_db)
    token = login_as_test_seller(client)

    category = test_db.scalar(
        select(Category).where(Category.id == product.category_id)
    )

    assert category is not None

    category.is_active = False
    test_db.commit()

    response = client.post(
        f"/api/v1/products/{product.id}/variants",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "sku": "NEXORA-INACTIVE-CATEGORY-001",
            "price": "999.99",
            "attributes": {
                "ram": "16GB",
            },
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Category is not active"


def test_seller_can_update_own_product_variant_details(client, test_db):
    product = get_test_product(test_db)
    token = login_as_test_seller(client)

    variant = test_db.scalar(
        select(ProductVariant).where(
            ProductVariant.sku == "NEXORA-PRO-16-512"
        )
    )

    assert variant is not None
    assert variant.product_id == product.id

    response = client.put(
        f"/api/v1/products/{product.id}/variants/{variant.id}/details",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "sku": "NEXORA-PRO-16-512-UPDATED",
            "price": "1499.99",
            "attributes": {
                "color": "Black",
                "ram": "32GB",
                "storage": "1TB",
            },
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == str(variant.id)
    assert data["product_id"] == str(product.id)
    assert data["sku"] == "NEXORA-PRO-16-512-UPDATED"
    assert data["price"] == "1499.99"
    assert data["attributes"] == {
        "color": "Black",
        "ram": "32GB",
        "storage": "1TB",
    }

    updated_variant = test_db.get(ProductVariant, variant.id)

    assert updated_variant is not None

    test_db.refresh(updated_variant)

    assert updated_variant.sku == "NEXORA-PRO-16-512-UPDATED"
    assert updated_variant.price == Decimal("1499.99")

    # Restore canonical variant state for subsequent tests.
    updated_variant.sku = "NEXORA-PRO-16-512"
    updated_variant.price = Decimal("1399.99")
    updated_variant.attributes = {
        "color": "Silver",
        "ram": "16GB",
        "storage": "512GB",
    }
    test_db.commit()


def test_seller_cannot_update_another_sellers_product_variant_details(
    client,
    test_db,
):
    product = get_test_product(test_db)

    other_user = test_db.scalar(
        select(User).where(
            User.email == "other.test.seller@nexora.local"
        )
    )

    assert other_user is not None

    other_seller = test_db.scalar(
        select(Seller).where(
            Seller.user_id == other_user.id
        )
    )

    assert other_seller is not None

    token_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "other.test.seller@nexora.local",
            "password": "TestPassword123!",
        },
    )

    assert token_response.status_code == 200

    token = token_response.json()["access_token"]

    variant = test_db.scalar(
        select(ProductVariant).where(
            ProductVariant.sku == "NEXORA-PRO-16-512"
        )
    )

    assert variant is not None

    response = client.put(
        f"/api/v1/products/{product.id}/variants/{variant.id}/details",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "price": "1499.99",
        },
    )

    assert response.status_code == 403


def test_update_product_variant_details_requires_authentication(
    client,
    test_db,
):
    product = get_test_product(test_db)

    variant = test_db.scalar(
        select(ProductVariant).where(
            ProductVariant.sku == "NEXORA-PRO-16-512"
        )
    )

    assert variant is not None

    response = client.put(
        f"/api/v1/products/{product.id}/variants/{variant.id}/details",
        json={
            "price": "1499.99",
        },
    )

    assert response.status_code == 401


def test_update_product_variant_details_rejects_duplicate_sku(
    client,
    test_db,
):
    product = get_test_product(test_db)
    token = login_as_test_seller(client)

    variant = test_db.scalar(
        select(ProductVariant).where(
            ProductVariant.sku == "NEXORA-PRO-16-512"
        )
    )

    assert variant is not None

    other_variant = ProductVariant(
        product_id=product.id,
        sku="NEXORA-DUPLICATE-TARGET",
        price=Decimal("1199.99"),
        attributes={},
    )

    test_db.add(other_variant)
    test_db.commit()
    test_db.refresh(other_variant)

    response = client.put(
        f"/api/v1/products/{product.id}/variants/{variant.id}/details",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "sku": "NEXORA-DUPLICATE-TARGET",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Product variant SKU already exists"


def test_update_product_variant_details_rejects_nonexistent_variant(
    client,
    test_db,
):
    product = get_test_product(test_db)
    token = login_as_test_seller(client)

    fake_variant_id = UUID("00000000-0000-0000-0000-000000000001")

    response = client.put(
        f"/api/v1/products/{product.id}/variants/{fake_variant_id}/details",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "price": "1499.99",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Product variant not found"


def test_seller_can_deactivate_own_product_variant(client, test_db):
    product = get_test_product(test_db)
    token = login_as_test_seller(client)

    variant = test_db.scalar(
        select(ProductVariant).where(
            ProductVariant.sku == "NEXORA-PRO-16-512"
        )
    )

    assert variant is not None
    assert variant.product_id == product.id
    assert variant.is_active is True

    response = client.patch(
        f"/api/v1/products/{product.id}/variants/{variant.id}",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "is_active": False,
        },
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is False

    test_db.refresh(variant)
    assert variant.is_active is False

    # Restore canonical state.
    variant.is_active = True
    test_db.commit()


def test_seller_can_reactivate_own_product_variant(client, test_db):
    product = get_test_product(test_db)
    token = login_as_test_seller(client)

    variant = test_db.scalar(
        select(ProductVariant).where(
            ProductVariant.sku == "NEXORA-PRO-16-512"
        )
    )

    assert variant is not None

    variant.is_active = False
    test_db.commit()

    response = client.patch(
        f"/api/v1/products/{product.id}/variants/{variant.id}",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "is_active": True,
        },
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is True

    test_db.refresh(variant)
    assert variant.is_active is True


def test_seller_cannot_change_another_sellers_product_variant_status(
    client,
    test_db,
):
    product = get_test_product(test_db)

    other_user = test_db.scalar(
        select(User).where(
            User.email == "other.test.seller@nexora.local"
        )
    )

    assert other_user is not None

    other_seller = test_db.scalar(
        select(Seller).where(
            Seller.user_id == other_user.id
        )
    )

    assert other_seller is not None

    token_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "other.test.seller@nexora.local",
            "password": "TestPassword123!",
        },
    )

    assert token_response.status_code == 200

    token = token_response.json()["access_token"]

    variant = test_db.scalar(
        select(ProductVariant).where(
            ProductVariant.sku == "NEXORA-PRO-16-512"
        )
    )

    assert variant is not None

    response = client.patch(
        f"/api/v1/products/{product.id}/variants/{variant.id}",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "is_active": False,
        },
    )

    assert response.status_code == 403


def test_update_product_variant_status_requires_authentication(
    client,
    test_db,
):
    product = get_test_product(test_db)

    variant = test_db.scalar(
        select(ProductVariant).where(
            ProductVariant.sku == "NEXORA-PRO-16-512"
        )
    )

    assert variant is not None

    response = client.patch(
        f"/api/v1/products/{product.id}/variants/{variant.id}",
        json={
            "is_active": False,
        },
    )

    assert response.status_code == 401


def test_update_product_variant_status_rejects_nonexistent_variant(
    client,
    test_db,
):
    product = get_test_product(test_db)
    token = login_as_test_seller(client)

    fake_variant_id = UUID("00000000-0000-0000-0000-000000000002")

    response = client.patch(
        f"/api/v1/products/{product.id}/variants/{fake_variant_id}",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "is_active": False,
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Product variant not found"

def test_list_products_pagination(client, test_db):
    response = client.get(
        "/api/v1/products",
        params={
            "page": 1,
            "page_size": 2,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["page"] == 1
    assert data["page_size"] == 2
    assert data["total"] >= 2
    assert len(data["items"]) == 2


def test_list_products_second_page(client, test_db):
    first_response = client.get(
        "/api/v1/products",
        params={
            "page": 1,
            "page_size": 2,
        },
    )

    assert first_response.status_code == 200

    first_data = first_response.json()

    second_response = client.get(
        "/api/v1/products",
        params={
            "page": 2,
            "page_size": 2,
        },
    )

    assert second_response.status_code == 200

    second_data = second_response.json()

    assert second_data["page"] == 2
    assert second_data["page_size"] == 2

    first_ids = {item["id"] for item in first_data["items"]}
    second_ids = {item["id"] for item in second_data["items"]}

    assert first_ids.isdisjoint(second_ids)


def test_list_products_rejects_invalid_page(client):
    response = client.get(
        "/api/v1/products",
        params={
            "page": 0,
        },
    )

    assert response.status_code == 422


def test_list_products_rejects_invalid_page_size(client):
    response = client.get(
        "/api/v1/products",
        params={
            "page_size": 101,
        },
    )

    assert response.status_code == 422

def test_list_products_sort_price_ascending(client):
    response = client.get(
        "/api/v1/products",
        params={"sort": "price_asc"},
    )

    assert response.status_code == 200

    prices = [
        float(item["base_price"])
        for item in response.json()["items"]
    ]

    assert prices == sorted(prices)


def test_list_products_sort_price_descending(client):
    response = client.get(
        "/api/v1/products",
        params={"sort": "price_desc"},
    )

    assert response.status_code == 200

    prices = [
        float(item["base_price"])
        for item in response.json()["items"]
    ]

    assert prices == sorted(prices, reverse=True)


def test_list_products_rejects_invalid_sort(client):
    response = client.get(
        "/api/v1/products",
        params={"sort": "invalid"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid sort option"

def test_list_products_filters_by_category(client, test_db):
    product = get_test_product(test_db)

    response = client.get(
        "/api/v1/products",
        params={"category_id": product.category_id},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total"] >= 1

    for item in data["items"]:
        assert item["category_id"] == product.category_id

def test_list_products_rejects_invalid_category_id(client):
    response = client.get(
        "/api/v1/products",
        params={"category_id": 0},
    )

    assert response.status_code == 422

def test_list_products_filters_by_seller(client, test_db):
    product = get_test_product(test_db)

    response = client.get(
        "/api/v1/products",
        params={"seller_id": product.seller_id},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total"] >= 1

    for item in data["items"]:
        assert item["seller_id"] == product.seller_id


def test_list_products_rejects_invalid_seller_id(client):
    response = client.get(
        "/api/v1/products",
        params={"seller_id": 0},
    )

    assert response.status_code == 422

def test_list_products_filters_by_min_price(client, test_db):
    product = get_test_product(test_db)

    response = client.get(
        "/api/v1/products",
        params={
            "min_price": str(product.base_price),
        },
    )

    assert response.status_code == 200

    data = response.json()

    for item in data["items"]:
        assert Decimal(item["base_price"]) >= product.base_price


def test_list_products_filters_by_max_price(client, test_db):
    product = get_test_product(test_db)

    response = client.get(
        "/api/v1/products",
        params={
            "max_price": str(product.base_price),
        },
    )

    assert response.status_code == 200

    data = response.json()

    for item in data["items"]:
        assert Decimal(item["base_price"]) <= product.base_price


def test_list_products_filters_by_price_range(client, test_db):
    response = client.get(
        "/api/v1/products",
        params={
            "min_price": "500",
            "max_price": "1500",
        },
    )

    assert response.status_code == 200

    data = response.json()

    for item in data["items"]:
        price = Decimal(item["base_price"])
        assert Decimal("500") <= price <= Decimal("1500")


def test_list_products_rejects_invalid_min_price(client):
    response = client.get(
        "/api/v1/products",
        params={"min_price": 0},
    )

    assert response.status_code == 422


def test_list_products_rejects_invalid_max_price(client):
    response = client.get(
        "/api/v1/products",
        params={"max_price": 0},
    )

    assert response.status_code == 422

def test_list_products_in_stock_filter(client, test_db):
    product = test_db.query(Product).first()
    variant = ProductVariant(
        product_id=product.id,
        sku="IN-STOCK-FILTER-001",
        price=product.base_price,
        attributes={},
        is_active=True,
    )
    test_db.add(variant)
    test_db.flush()

    inventory = Inventory(
        variant_id=variant.id,
        quantity=10,
        reserved_quantity=2,
        is_active=True,
    )
    test_db.add(inventory)
    test_db.commit()

    response = client.get("/api/v1/products?in_stock=true")

    assert response.status_code == 200

    data = response.json()
    product_ids = [item["id"] for item in data["items"]]

    assert str(product.id) in product_ids


def test_list_products_in_stock_excludes_product_with_fully_reserved_variant(
    client, test_db
):
    product = test_db.query(Product).first()

    for variant in product.variants:
        inventory = test_db.query(Inventory).filter(
            Inventory.variant_id == variant.id
        ).first()

        if inventory is not None:
            inventory.reserved_quantity = inventory.quantity

    test_db.commit()

    response = client.get("/api/v1/products?in_stock=true")

    assert response.status_code == 200

    data = response.json()
    product_ids = [item["id"] for item in data["items"]]

    assert str(product.id) not in product_ids

def test_get_product_includes_variant_availability(client, test_db):
    product = get_test_product(test_db)

    variant = test_db.scalar(
        select(ProductVariant).where(
            ProductVariant.sku == "NEXORA-PRO-16-512"
        )
    )

    assert variant is not None
    assert variant.product_id == product.id

    inventory = test_db.scalar(
        select(Inventory).where(
            Inventory.variant_id == variant.id
        )
    )

    assert inventory is not None

    inventory.quantity = 10
    inventory.reserved_quantity = 3
    inventory.is_active = True
    variant.is_active = True
    test_db.commit()

    response = client.get(
        f"/api/v1/products/{product.id}"
    )

    assert response.status_code == 200

    data = response.json()

    variants = data["variants"]

    matching_variant = next(
        item for item in variants
        if item["id"] == str(variant.id)
    )

    assert matching_variant["sku"] == variant.sku
    assert matching_variant["available_quantity"] == 7
    assert "reserved_quantity" not in matching_variant

def test_get_product_inactive_variant_has_zero_availability(client, test_db):
    product = get_test_product(test_db)

    variant = test_db.scalar(
        select(ProductVariant).where(
            ProductVariant.sku == "NEXORA-PRO-16-512"
        )
    )

    assert variant is not None

    inventory = test_db.scalar(
        select(Inventory).where(
            Inventory.variant_id == variant.id
        )
    )

    assert inventory is not None

    variant.is_active = False
    inventory.quantity = 10
    inventory.reserved_quantity = 0
    inventory.is_active = True

    test_db.commit()

    response = client.get(
        f"/api/v1/products/{product.id}"
    )

    assert response.status_code == 200

    data = response.json()

    matching_variant = next(
        item for item in data["variants"]
        if item["id"] == str(variant.id)
    )

    assert matching_variant["is_active"] is False
    assert matching_variant["available_quantity"] == 0

    # Restore canonical state.
    variant.is_active = True
    test_db.commit()

def test_get_product_inactive_inventory_has_zero_availability(client, test_db):
    product = get_test_product(test_db)

    variant = test_db.scalar(
        select(ProductVariant).where(
            ProductVariant.sku == "NEXORA-PRO-16-512"
        )
    )

    assert variant is not None

    inventory = test_db.scalar(
        select(Inventory).where(
            Inventory.variant_id == variant.id
        )
    )

    assert inventory is not None

    variant.is_active = True
    inventory.quantity = 10
    inventory.reserved_quantity = 0
    inventory.is_active = False

    test_db.commit()

    response = client.get(
        f"/api/v1/products/{product.id}"
    )

    assert response.status_code == 200

    data = response.json()

    matching_variant = next(
        item for item in data["variants"]
        if item["id"] == str(variant.id)
    )

    assert matching_variant["is_active"] is True
    assert matching_variant["available_quantity"] == 0

    # Restore canonical state.
    inventory.is_active = True
    test_db.commit()

def test_get_product_never_returns_negative_availability(client, test_db):
    product = get_test_product(test_db)

    variant = test_db.scalar(
        select(ProductVariant).where(
            ProductVariant.sku == "NEXORA-PRO-16-512"
        )
    )

    assert variant is not None

    inventory = test_db.scalar(
        select(Inventory).where(
            Inventory.variant_id == variant.id
        )
    )

    assert inventory is not None

    variant.is_active = True
    inventory.quantity = 2
    inventory.reserved_quantity = 5
    inventory.is_active = True

    test_db.commit()

    response = client.get(
        f"/api/v1/products/{product.id}"
    )

    assert response.status_code == 200

    data = response.json()

    matching_variant = next(
        item for item in data["variants"]
        if item["id"] == str(variant.id)
    )

    assert matching_variant["available_quantity"] == 0

    # Restore canonical state.
    inventory.quantity = 0
    inventory.reserved_quantity = 0
    test_db.commit()

def test_list_category_products_returns_own_products(client, test_db):
    product = get_test_product(test_db)

    category = test_db.scalar(
        select(Category).where(
            Category.id == product.category_id
        )
    )

    assert category is not None
    assert category.is_active is True

    response = client.get(
        f"/api/v1/categories/{category.slug}/products"
    )

    assert response.status_code == 200

    data = response.json()

    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data

    product_ids = {
        item["id"]
        for item in data["items"]
    }

    assert str(product.id) in product_ids

def test_list_category_products_includes_active_descendants(client, test_db):
    parent = Category(
        name="Test Electronics",
        slug="test-electronics",
        description="Parent test category",
        is_active=True,
    )
    test_db.add(parent)
    test_db.flush()

    child = Category(
        name="Test Laptops",
        slug="test-laptops",
        parent_id=parent.id,
        description="Child test category",
        is_active=True,
    )
    test_db.add(child)
    test_db.flush()

    product = get_test_product(test_db)
    original_category_id = product.category_id
    product.category_id = child.id

    test_db.commit()

    response = client.get(
        f"/api/v1/categories/{parent.slug}/products"
    )

    assert response.status_code == 200

    data = response.json()

    product_ids = {
        item["id"]
        for item in data["items"]
    }

    assert str(product.id) in product_ids

    # Restore canonical product state.
    product.category_id = original_category_id
    test_db.delete(child)
    test_db.delete(parent)
    test_db.commit()

def test_list_category_products_excludes_inactive_descendants(client, test_db):
    parent = Category(
        name="Test Electronics Inactive",
        slug="test-electronics-inactive",
        description="Parent test category",
        is_active=True,
    )
    test_db.add(parent)
    test_db.flush()

    child = Category(
        name="Test Laptops Inactive",
        slug="test-laptops-inactive",
        parent_id=parent.id,
        description="Inactive child test category",
        is_active=False,
    )
    test_db.add(child)
    test_db.flush()

    product = get_test_product(test_db)
    original_category_id = product.category_id
    product.category_id = child.id

    test_db.commit()

    response = client.get(
        f"/api/v1/categories/{parent.slug}/products"
    )

    assert response.status_code == 200

    data = response.json()

    product_ids = {
        item["id"]
        for item in data["items"]
    }

    assert str(product.id) not in product_ids

    # Restore canonical product state.
    product.category_id = original_category_id
    test_db.delete(child)
    test_db.delete(parent)
    test_db.commit()

def test_list_category_products_returns_not_found_for_unknown_slug(client):
    response = client.get(
        "/api/v1/categories/category-that-does-not-exist/products"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Category not found"

def test_list_products_searches_name(client):
    response = client.get("/api/v1/products?search=NEXORA%20Pro")

    assert response.status_code == 200

    data = response.json()

    assert data["total"] >= 1
    assert any(
        item["name"] == "NEXORA Pro Laptop"
        for item in data["items"]
    )


def test_list_products_searches_description(client):
    response = client.get("/api/v1/products?search=Test%20product")

    assert response.status_code == 200

    data = response.json()

    assert data["total"] >= 1
    assert any(
        item["name"] == "NEXORA Pro Laptop"
        for item in data["items"]
    )


def test_list_products_search_is_case_insensitive(client):
    response = client.get("/api/v1/products?search=nexora%20pro")

    assert response.status_code == 200

    data = response.json()

    assert data["total"] >= 1
    assert any(
        item["name"] == "NEXORA Pro Laptop"
        for item in data["items"]
    )


def test_list_products_search_no_match(client):
    response = client.get("/api/v1/products?search=DefinitelyNotARealProduct")

    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 0
    assert data["items"] == []

def test_list_products_pagination(client):
    first_response = client.get(
        "/api/v1/products?page=1&page_size=1"
    )

    second_response = client.get(
        "/api/v1/products?page=2&page_size=1"
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    first_data = first_response.json()
    second_data = second_response.json()

    assert first_data["page"] == 1
    assert second_data["page"] == 2
    assert first_data["page_size"] == 1
    assert second_data["page_size"] == 1

    assert len(first_data["items"]) <= 1
    assert len(second_data["items"]) <= 1

    if first_data["items"] and second_data["items"]:
        assert first_data["items"][0]["id"] != second_data["items"][0]["id"]

def test_list_products_invalid_sort(client):
    response = client.get("/api/v1/products?sort=invalid")

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid sort option"

def test_list_products_rejects_invalid_pagination(client):
    response = client.get("/api/v1/products?page=0")

    assert response.status_code == 422

    response = client.get("/api/v1/products?page_size=101")

    assert response.status_code == 422

def test_list_products_combines_search_and_price_filter(client):
    response = client.get(
        "/api/v1/products"
        "?search=NEXORA%20Pro"
        "&min_price=1"
        "&max_price=100000"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total"] >= 1

    for item in data["items"]:
        assert "nexora pro" in item["name"].lower()
        assert 1 <= float(item["base_price"]) <= 100000

    def test_list_products_normalizes_search_whitespace(client):
        response = client.get(
        "/api/v1/products?search=%20%20NEXORA%20%20%20Pro%20%20"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total"] >= 1
    assert any(
        "nexora pro" in item["name"].lower()
        for item in data["items"]
    )


def test_list_products_supports_multi_token_search(client):
    response = client.get(
        "/api/v1/products?search=laptop%2016gb"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total"] >= 1

    for item in data["items"]:
        searchable_text = (
            f"{item['name']} {item.get('description', '')}"
        ).lower()

        assert "laptop" in searchable_text
        assert "16gb" in searchable_text


def test_list_products_ranks_exact_name_match_first(client):
    response = client.get(
        "/api/v1/products?search=NEXORA%20Pro"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total"] >= 1

    first_product = data["items"][0]

    assert first_product["name"].lower() == "nexora pro laptop"


def test_list_products_rejects_whitespace_only_search(client):
    response = client.get(
        "/api/v1/products?search=%20%20%20"
    )

    assert response.status_code == 422


def test_list_products_search_preserves_pagination(client):
    response = client.get(
        "/api/v1/products"
        "?search=NEXORA"
        "&page=1"
        "&page_size=1"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total"] >= 1
    assert len(data["items"]) == 1
    assert data["page"] == 1
    assert data["page_size"] == 1

def test_list_products_normalizes_search_whitespace(client):
    response = client.get(
        "/api/v1/products?search=%20%20NEXORA%20%20%20Pro%20%20"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total"] >= 1
    assert any(
        "nexora pro" in item["name"].lower()
        for item in data["items"]
    )


def test_list_products_supports_multi_token_search(client):
    response = client.get(
        "/api/v1/products?search=NEXORA%20Laptop"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total"] >= 1

    for item in data["items"]:
        searchable_text = (
            f"{item['name']} {item.get('description', '')}"
        ).lower()

        assert "nexora" in searchable_text
        assert "laptop" in searchable_text


def test_list_products_ranks_exact_name_match_first(client):
    response = client.get(
        "/api/v1/products?search=NEXORA%20Pro"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total"] >= 1

    first_product = data["items"][0]

    assert first_product["name"].lower() == "nexora pro laptop"


def test_list_products_rejects_whitespace_only_search(client):
    response = client.get(
        "/api/v1/products?search=%20%20%20"
    )

    assert response.status_code == 422


def test_list_products_search_preserves_pagination(client):
    response = client.get(
        "/api/v1/products"
        "?search=NEXORA"
        "&page=1"
        "&page_size=1"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total"] >= 1
    assert len(data["items"]) == 1
    assert data["page"] == 1
    assert data["page_size"] == 1