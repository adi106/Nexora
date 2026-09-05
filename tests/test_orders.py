from datetime import datetime, timedelta, timezone

from backend.worker.reservation_cleanup import run_cleanup_once

from sqlalchemy import delete, select

from backend.app.core.config import settings
from backend.app.services.order_service import create_order_from_cart



from backend.app.models import (
    Address,
    Cart,
    CartItem,
    Inventory,
    ProductVariant,
    User,
)
from backend.app.models.cart import CartStatus


TEST_EMAIL = "secure.test@nexora.com"
TEST_PASSWORD = "TestPassword123!"
TEST_SKU = "NEXORA-PRO-16-512"


def login(client):
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": TEST_EMAIL,
            "password": TEST_PASSWORD,
        },
    )

    assert response.status_code == 200

    return response.json()["access_token"]


def get_test_variant(test_db):
    variant = test_db.scalar(
        select(ProductVariant).where(
            ProductVariant.sku == TEST_SKU
        )
    )

    assert variant is not None

    return variant


def get_test_user(test_db):
    user = test_db.scalar(
        select(User).where(
            User.email == TEST_EMAIL
        )
    )

    assert user is not None

    return user


def get_test_address(test_db):
    user = get_test_user(test_db)

    address = test_db.scalar(
        select(Address).where(
            Address.user_id == user.id
        )
    )

    assert address is not None

    return address


def get_test_cart(test_db):
    user = get_test_user(test_db)

    cart = test_db.scalar(
        select(Cart).where(
            Cart.user_id == user.id,
            Cart.status == CartStatus.ACTIVE,
        )
    )

    assert cart is not None

    return cart


def test_create_order_requires_authentication(client, test_db):
    address = get_test_address(test_db)

    response = client.post(
        "/api/v1/orders",
        json={
            "address_id": str(address.id),
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_get_orders_requires_authentication(client):
    response = client.get(
        "/api/v1/orders"
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_get_single_order_requires_authentication(client):
    response = client.get(
        "/api/v1/orders/3481b84c-0de6-45a9-8dbb-e3f57ec6d3f5"
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_create_order_with_authenticated_user(client, test_db):
    token = login(client)

    variant = get_test_variant(test_db)
    address = get_test_address(test_db)

    cart_response = client.get(
        "/api/v1/cart",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert cart_response.status_code == 200

    add_response = client.post(
        "/api/v1/cart/items",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "variant_id": str(variant.id),
            "quantity": 1,
        },
    )

    assert add_response.status_code == 201

    order_response = client.post(
        "/api/v1/orders",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "address_id": str(address.id),
        },
    )

    assert order_response.status_code == 201

    data = order_response.json()

    assert "id" in data
    assert data["status"] == "pending"
    assert data["total_amount"] == "1399.99"
    assert data["shipping_full_name"] == "Secure Test"
    assert data["shipping_city"] == "Hamilton"
    assert data["shipping_country_code"] == "NZ"

    assert len(data["items"]) == 1
    assert data["items"][0]["sku"] == TEST_SKU
    assert data["items"][0]["quantity"] == 1
    assert data["items"][0]["subtotal"] == "1399.99"


def test_create_order_reserves_inventory(client, test_db):
    token = login(client)

    variant = get_test_variant(test_db)
    address = get_test_address(test_db)

    inventory = test_db.scalar(
        select(Inventory).where(
            Inventory.variant_id == variant.id
        )
    )

    assert inventory is not None

    reserved_before = inventory.reserved_quantity

    add_response = client.post(
        "/api/v1/cart/items",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "variant_id": str(variant.id),
            "quantity": 2,
        },
    )

    assert add_response.status_code == 201

    order_response = client.post(
        "/api/v1/orders",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "address_id": str(address.id),
        },
    )

    assert order_response.status_code == 201

    data = order_response.json()

    assert data["status"] == "pending"
    assert data["items"][0]["quantity"] == 2

    test_db.expire_all()

    inventory = test_db.scalar(
        select(Inventory).where(
            Inventory.variant_id == variant.id
        )
    )

    assert inventory is not None
    assert inventory.reserved_quantity == reserved_before + 2


def test_create_order_rejects_insufficient_stock(client, test_db):
    token = login(client)

    variant = get_test_variant(test_db)
    address = get_test_address(test_db)

    inventory = test_db.scalar(
        select(Inventory).where(
            Inventory.variant_id == variant.id
        )
    )

    assert inventory is not None

    available_stock = (
        inventory.quantity - inventory.reserved_quantity
    )

    requested_quantity = available_stock + 1

    add_response = client.post(
        "/api/v1/cart/items",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "variant_id": str(variant.id),
            "quantity": 1,
        },
    )

    assert add_response.status_code == 201

    cart = get_test_cart(test_db)

    cart_item = test_db.scalar(
        select(CartItem).where(
            CartItem.cart_id == cart.id,
            CartItem.variant_id == variant.id,
        )
    )

    assert cart_item is not None

    # Deliberately bypass the cart API's stock validation.
    # This tests the checkout service's own stock protection.
    cart_item.quantity = requested_quantity

    test_db.commit()

    order_response = client.post(
        "/api/v1/orders",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "address_id": str(address.id),
        },
    )

    assert order_response.status_code == 400
    assert "items available" in order_response.json()["detail"]


def test_payment_success_updates_order_and_inventory(client, test_db):
    token = login(client)

    variant = get_test_variant(test_db)
    address = get_test_address(test_db)

    inventory = test_db.scalar(
        select(Inventory).where(
            Inventory.variant_id == variant.id
        )
    )

    assert inventory is not None

    quantity_before = inventory.quantity
    reserved_before = inventory.reserved_quantity

    add_response = client.post(
        "/api/v1/cart/items",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "variant_id": str(variant.id),
            "quantity": 1,
        },
    )

    assert add_response.status_code == 201

    order_response = client.post(
        "/api/v1/orders",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "address_id": str(address.id),
        },
    )

    assert order_response.status_code == 201

    order_id = order_response.json()["id"]

    payment_response = client.post(
        f"/api/v1/orders/{order_id}/payment",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "succeed": True,
        },
    )

    assert payment_response.status_code == 200

    data = payment_response.json()

    assert data["status"] == "paid"

    test_db.expire_all()

    inventory = test_db.scalar(
        select(Inventory).where(
            Inventory.variant_id == variant.id
        )
    )

    assert inventory is not None

    assert inventory.quantity == quantity_before - 1
    assert inventory.reserved_quantity == reserved_before


def test_payment_failure_cancels_order_and_releases_inventory(
    client,
    test_db,
):
    token = login(client)

    variant = get_test_variant(test_db)
    address = get_test_address(test_db)

    inventory = test_db.scalar(
        select(Inventory).where(
            Inventory.variant_id == variant.id
        )
    )

    assert inventory is not None

    quantity_before = inventory.quantity
    reserved_before = inventory.reserved_quantity

    add_response = client.post(
        "/api/v1/cart/items",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "variant_id": str(variant.id),
            "quantity": 1,
        },
    )

    assert add_response.status_code == 201

    order_response = client.post(
        "/api/v1/orders",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "address_id": str(address.id),
        },
    )

    assert order_response.status_code == 201

    order_id = order_response.json()["id"]

    payment_response = client.post(
        f"/api/v1/orders/{order_id}/payment",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "succeed": False,
        },
    )

    assert payment_response.status_code == 200

    data = payment_response.json()

    assert data["status"] == "cancelled"

    test_db.expire_all()

    inventory = test_db.scalar(
        select(Inventory).where(
            Inventory.variant_id == variant.id
        )
    )

    assert inventory is not None

    assert inventory.quantity == quantity_before
    assert inventory.reserved_quantity == reserved_before

def test_create_order_sets_reservation_expiry(client, test_db):
    token = login(client)
    variant = get_test_variant(test_db)
    address = get_test_address(test_db)

    add_response = client.post(
        "/api/v1/cart/items",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "variant_id": str(variant.id),
            "quantity": 1,
        },
    )

    assert add_response.status_code == 201

    before_creation = datetime.now(timezone.utc)

    order_response = client.post(
        "/api/v1/orders",
        headers={"Authorization": f"Bearer {token}"},
        json={"address_id": str(address.id)},
    )

    after_creation = datetime.now(timezone.utc)

    assert order_response.status_code == 201

    data = order_response.json()

    assert data["status"] == "pending"
    assert data["reservation_expires_at"] is not None

    reservation_expires_at = datetime.fromisoformat(
        data["reservation_expires_at"].replace("Z", "+00:00")
    )

    expected_before = (
        before_creation
        + timedelta(minutes=settings.reservation_expiry_minutes)
    )
    expected_after = (
        after_creation
        + timedelta(minutes=settings.reservation_expiry_minutes)
    )

    assert expected_before <= reservation_expires_at <= expected_after


def test_expire_pending_order_releases_inventory(client, test_db):
    from backend.app.services.reservation_service import expire_pending_orders

    token = login(client)
    variant = get_test_variant(test_db)
    address = get_test_address(test_db)

    add_response = client.post(
        "/api/v1/cart/items",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "variant_id": str(variant.id),
            "quantity": 3,
        },
    )

    assert add_response.status_code == 201

    order_response = client.post(
        "/api/v1/orders",
        headers={"Authorization": f"Bearer {token}"},
        json={"address_id": str(address.id)},
    )

    assert order_response.status_code == 201

    order_id = order_response.json()["id"]

    test_db.expire_all()

    inventory = test_db.scalar(
        select(Inventory).where(
            Inventory.variant_id == variant.id
        )
    )

    assert inventory is not None
    assert inventory.reserved_quantity == 3

    order = test_db.get(
        __import__(
            "backend.app.models.order",
            fromlist=["Order"],
        ).Order,
        order_id,
    )

    assert order is not None

    expired_count = expire_pending_orders(
        test_db,
        now=order.reservation_expires_at + timedelta(seconds=1),
    )

    assert expired_count == 1

    test_db.expire_all()

    inventory = test_db.scalar(
        select(Inventory).where(
            Inventory.variant_id == variant.id
        )
    )

    assert inventory is not None
    assert inventory.reserved_quantity == 0

    order = test_db.get(
        __import__(
            "backend.app.models.order",
            fromlist=["Order"],
        ).Order,
        order_id,
    )

    assert order is not None
    assert order.status.value == "cancelled"


def test_expire_pending_order_is_idempotent(client, test_db):
    from backend.app.services.reservation_service import expire_pending_orders

    token = login(client)
    variant = get_test_variant(test_db)
    address = get_test_address(test_db)

    add_response = client.post(
        "/api/v1/cart/items",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "variant_id": str(variant.id),
            "quantity": 2,
        },
    )

    assert add_response.status_code == 201

    order_response = client.post(
        "/api/v1/orders",
        headers={"Authorization": f"Bearer {token}"},
        json={"address_id": str(address.id)},
    )

    assert order_response.status_code == 201

    order_id = order_response.json()["id"]

    test_db.expire_all()

    order = test_db.get(
        __import__(
            "backend.app.models.order",
            fromlist=["Order"],
        ).Order,
        order_id,
    )

    assert order is not None

    expiry_time = order.reservation_expires_at + timedelta(seconds=1)

    first_count = expire_pending_orders(
        test_db,
        now=expiry_time,
    )

    assert first_count == 1

    test_db.expire_all()

    inventory = test_db.scalar(
        select(Inventory).where(
            Inventory.variant_id == variant.id
        )
    )

    assert inventory is not None
    assert inventory.reserved_quantity == 0

    second_count = expire_pending_orders(
        test_db,
        now=expiry_time + timedelta(minutes=1),
    )

    assert second_count == 0

    test_db.expire_all()

    inventory = test_db.scalar(
        select(Inventory).where(
            Inventory.variant_id == variant.id
        )
    )

    assert inventory is not None
    assert inventory.reserved_quantity == 0


def test_reservation_cleanup_worker_expires_orders(client, test_db):
    token = login(client)
    variant = get_test_variant(test_db)
    address = get_test_address(test_db)

    add_response = client.post(
        "/api/v1/cart/items",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "variant_id": str(variant.id),
            "quantity": 4,
        },
    )

    assert add_response.status_code == 201

    order_response = client.post(
        "/api/v1/orders",
        headers={"Authorization": f"Bearer {token}"},
        json={"address_id": str(address.id)},
    )

    assert order_response.status_code == 201

    order_id = order_response.json()["id"]

    test_db.expire_all()

    order = test_db.get(
        __import__(
            "backend.app.models.order",
            fromlist=["Order"],
        ).Order,
        order_id,
    )

    assert order is not None
    assert order.reservation_expires_at is not None

    # Move the reservation expiry into the past.
    order.reservation_expires_at = (
        datetime.now(timezone.utc) - timedelta(seconds=1)
    )
    test_db.commit()

    expired_count = run_cleanup_once(test_db)

    assert expired_count == 1

    test_db.expire_all()

    order = test_db.get(
        __import__(
            "backend.app.models.order",
            fromlist=["Order"],
        ).Order,
        order_id,
    )

    assert order is not None
    assert order.status.value == "cancelled"

    inventory = test_db.scalar(
        select(Inventory).where(
            Inventory.variant_id == variant.id
        )
    )

    assert inventory is not None
    assert inventory.reserved_quantity == 0


def test_expired_order_cannot_be_paid(client, test_db):
    token = login(client)
    variant = get_test_variant(test_db)
    address = get_test_address(test_db)

    add_response = client.post(
        "/api/v1/cart/items",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "variant_id": str(variant.id),
            "quantity": 1,
        },
    )

    assert add_response.status_code == 201

    order_response = client.post(
        "/api/v1/orders",
        headers={"Authorization": f"Bearer {token}"},
        json={"address_id": str(address.id)},
    )

    assert order_response.status_code == 201

    order_id = order_response.json()["id"]

    test_db.expire_all()

    order = test_db.get(
        __import__(
            "backend.app.models.order",
            fromlist=["Order"],
        ).Order,
        order_id,
    )

    assert order is not None
    assert order.reservation_expires_at is not None

    order.reservation_expires_at = (
        datetime.now(timezone.utc) - timedelta(seconds=1)
    )
    test_db.commit()

    payment_response = client.post(
        f"/api/v1/orders/{order_id}/payment",
        headers={"Authorization": f"Bearer {token}"},
        json={"succeed": True},
    )

    assert payment_response.status_code == 400
    assert payment_response.json()["detail"] == (
        "Order reservation has expired"
    )

    test_db.expire_all()

    order = test_db.get(
        __import__(
            "backend.app.models.order",
            fromlist=["Order"],
        ).Order,
        order_id,
    )

    assert order is not None
    assert order.status.value == "cancelled"

    inventory = test_db.scalar(
        select(Inventory).where(
            Inventory.variant_id == variant.id
        )
    )

    assert inventory is not None
    assert inventory.reserved_quantity == 0


def test_concurrent_checkout_cannot_oversell(test_db):
    from threading import Barrier, Thread

    from sqlalchemy.orm import sessionmaker
    from backend.app.models import Cart, CartItem, CartStatus, User
    from backend.app.services.order_service import create_order_from_cart

    TestSessionLocal = sessionmaker(
        bind=test_db.get_bind(),
        autoflush=False,
        autocommit=False,
)

    variant = get_test_variant(test_db)
    address = get_test_address(test_db)
    first_user = get_test_user(test_db)
    first_user_id = first_user.id
    first_address_id = address.id

    # Reduce stock to exactly one available unit.
    inventory = test_db.scalar(
        select(Inventory).where(
            Inventory.variant_id == variant.id
        )
    )
    assert inventory is not None

    inventory.quantity = 1
    inventory.reserved_quantity = 0
    test_db.commit()

    # Create or reuse a second test user.
    second_user = test_db.scalar(
        select(User).where(
            User.email == "concurrency.test@nexora.com"
        )
    )

    if second_user is None:
        second_user = User(
            email="concurrency.test@nexora.com",
            password_hash="unused",
            first_name="Concurrency",
            last_name="Test",
        )
        test_db.add(second_user)
        test_db.flush()

    second_user_id = second_user.id

    second_address = test_db.scalar(
        select(Address).where(
            Address.user_id == second_user.id
        )
    )

    if second_address is None:
        second_address = Address(
            user_id=second_user.id,
            address_line1="456 Test Street",
            city="Hamilton",
            region="Waikato",
            postal_code="3204",
            country_code="NZ",
            is_default=True,
        )
        test_db.add(second_address)
        test_db.flush()

    second_address_id = second_address.id

    second_cart = test_db.scalar(
        select(Cart).where(
            Cart.user_id == second_user.id,
            Cart.status == CartStatus.ACTIVE,
        )
    )

    if second_cart is None:
        second_cart = Cart(
            user_id=second_user.id,
            status=CartStatus.ACTIVE,
        )
        test_db.add(second_cart)
        test_db.flush()

    first_cart = get_test_cart(test_db)

    # Clear existing items from both carts.
    test_db.execute(
        delete(CartItem).where(
            CartItem.cart_id.in_(
                [first_cart.id, second_cart.id]
            )
        )
    )

    # Both customers want the same final unit.
    test_db.add_all(
        [
            CartItem(
                cart_id=first_cart.id,
                variant_id=variant.id,
                quantity=1,
            ),
            CartItem(
                cart_id=second_cart.id,
                variant_id=variant.id,
                quantity=1,
            ),
        ]
    )

    test_db.commit()

    # Capture plain IDs before the threaded sessions start.
    variant_id = variant.id

    barrier = Barrier(2)
    results = []

    def checkout(user_id, address_id):
        db = TestSessionLocal()

        try:
            user = db.get(User, user_id)
            assert user is not None

            barrier.wait()

            try:
                order = create_order_from_cart(
                    db,
                    user,
                    address_id,
                )
                results.append(("success", order.id))

            except Exception as exc:
                db.rollback()
                results.append(("failure", repr(exc)))

        finally:
            db.close()

    threads = [
        Thread(
            target=checkout,
            args=(first_user_id, first_address_id),
        ),
        Thread(
            target=checkout,
            args=(second_user_id, second_address_id),
        ),
    ]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    print("\nCONCURRENCY RESULTS:", results)

    successes = [
        result
        for result in results
        if result[0] == "success"
    ]

    failures = [
        result
        for result in results
        if result[0] == "failure"
    ]

    assert len(successes) == 1
    assert len(failures) == 1

    test_db.expire_all()

    inventory = test_db.scalar(
        select(Inventory).where(
            Inventory.variant_id == variant_id
        )
    )

    assert inventory is not None
    assert inventory.quantity == 1
    assert inventory.reserved_quantity == 1


def test_concurrent_checkout_same_cart_creates_only_one_order(test_db):
    from threading import Barrier, Thread

    from sqlalchemy.orm import sessionmaker

    from backend.app.models import CartItem
    from backend.app.services.order_service import create_order_from_cart

    TestSessionLocal = sessionmaker(
        bind=test_db.get_bind(),
        autoflush=False,
        autocommit=False,
    )

    user = get_test_user(test_db)
    address = get_test_address(test_db)
    cart = get_test_cart(test_db)
    variant = get_test_variant(test_db)

    inventory = test_db.scalar(
        select(Inventory).where(
            Inventory.variant_id == variant.id
        )
    )
    assert inventory is not None

    # Give enough stock that inventory availability itself
    # does not prevent the second checkout.
    inventory.quantity = 10
    inventory.reserved_quantity = 0

    test_db.execute(
        delete(CartItem).where(
            CartItem.cart_id == cart.id
        )
    )

    test_db.add(
        CartItem(
            cart_id=cart.id,
            variant_id=variant.id,
            quantity=1,
        )
    )

    cart.status = CartStatus.ACTIVE
    test_db.commit()

    user_id = user.id
    address_id = address.id

    barrier = Barrier(2)
    results = []

    def checkout():
        db = TestSessionLocal()

        try:
            current_user = db.get(User, user_id)
            assert current_user is not None

            barrier.wait()

            try:
                order = create_order_from_cart(
                    db,
                    current_user,
                    address_id,
                )
                results.append(("success", order.id))

            except Exception as exc:
                db.rollback()
                results.append(("failure", repr(exc)))

        finally:
            db.close()

    threads = [
        Thread(target=checkout),
        Thread(target=checkout),
    ]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    print("\nSAME CART CONCURRENCY RESULTS:", results)

    successes = [
        result
        for result in results
        if result[0] == "success"
    ]

    failures = [
        result
        for result in results
        if result[0] == "failure"
    ]

    assert len(successes) == 1
    assert len(failures) == 1