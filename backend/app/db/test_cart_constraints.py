from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from backend.app.db.session import SessionLocal
from backend.app.models import Cart, CartItem, ProductVariant, User


def main():
    db = SessionLocal()

    try:
        user = db.scalar(
            select(User).where(User.email == "test.seller@nexora.local")
        )

        variant = db.scalar(
            select(ProductVariant)
        )

        if not user or not variant:
            raise RuntimeError("Seed data not found")

        # 1. Create active cart
        cart = Cart(user_id=user.id)
        db.add(cart)
        db.commit()
        db.refresh(cart)

        print("Active cart created:", cart.id)

        # 2. Add item
        item = CartItem(
            cart_id=cart.id,
            variant_id=variant.id,
            quantity=2,
        )

        db.add(item)
        db.commit()

        print("Cart item created")

        # 3. Try duplicate variant in same cart
        duplicate = CartItem(
            cart_id=cart.id,
            variant_id=variant.id,
            quantity=1,
        )

        db.add(duplicate)

        try:
            db.commit()
            print("ERROR: duplicate cart item was allowed")
        except IntegrityError:
            db.rollback()
            print("PASS: duplicate cart item blocked")

        # 4. Try second active cart for same user
        second_cart = Cart(user_id=user.id)
        db.add(second_cart)

        try:
            db.commit()
            print("ERROR: second active cart was allowed")
        except IntegrityError:
            db.rollback()
            print("PASS: second active cart blocked")

    finally:
        db.close()


if __name__ == "__main__":
    main()