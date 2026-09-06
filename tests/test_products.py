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

    product_ids = {item["id"] for item in data}

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