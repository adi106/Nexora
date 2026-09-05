import uuid

from backend.app.db.session import SessionLocal
from backend.app.models.cart import Cart, CartStatus
from backend.app.models.cart_item import CartItem
from backend.app.models.product_variant import ProductVariant
from backend.app.models.user import User


TEST_EMAIL = "secure.test@nexora.com"
TEST_SKU = "NEXORA-PRO-16-512"


db = SessionLocal()

try:
    user = (
        db.query(User)
        .filter(User.email == TEST_EMAIL)
        .first()
    )

    if user is None:
        raise RuntimeError(f"User not found: {TEST_EMAIL}")

    cart = (
        db.query(Cart)
        .filter(
            Cart.user_id == user.id,
            Cart.status == CartStatus.ACTIVE,
        )
        .first()
    )

    if cart is None:
        cart = Cart(
            user_id=user.id,
            status=CartStatus.ACTIVE,
        )
        db.add(cart)
        db.flush()

    variant = (
        db.query(ProductVariant)
        .filter(ProductVariant.sku == TEST_SKU)
        .first()
    )

    if variant is None:
        raise RuntimeError(f"Variant not found: {TEST_SKU}")

    existing_item = (
        db.query(CartItem)
        .filter(
            CartItem.cart_id == cart.id,
            CartItem.variant_id == variant.id,
        )
        .first()
    )

    if existing_item:
        print("Cart item already exists:")
        print("Quantity:", existing_item.quantity)
    else:
        cart_item = CartItem(
            cart_id=cart.id,
            variant_id=variant.id,
            quantity=1,
        )

        db.add(cart_item)
        db.commit()

        print("Test cart item created:")
        print("Cart ID:", cart.id)
        print("Variant:", variant.sku)
        print("Quantity:", 1)

finally:
    db.close()