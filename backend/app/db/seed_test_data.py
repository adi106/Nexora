from decimal import Decimal

from sqlalchemy import select

from backend.app.db.session import SessionLocal
from backend.app.models import (
    Category,
    Inventory,
    Product,
    ProductVariant,
    Role,
    Seller,
    User,
    UserRole,
)


def seed_test_data():
    db = SessionLocal()

    try:
        # 1. Create test user
        user = User(
            email="test.seller@nexora.local",
            password_hash="development-only-hash",
            first_name="Test",
            last_name="Seller",
        )
        db.add(user)
        db.flush()

        # 2. Assign seller role
        seller_role = db.scalar(
            select(Role).where(Role.name == "seller")
        )

        if not seller_role:
            raise RuntimeError("Seller role not found")

        user_role = UserRole(
            user_id=user.id,
            role_id=seller_role.id,
        )
        db.add(user_role)

        # 3. Create seller
        seller = Seller(
            user_id=user.id,
            store_name="NEXORA Test Store",
            store_slug="nexora-test-store",
            description="Development test seller",
        )
        db.add(seller)
        db.flush()

        # 4. Create category
        category = Category(
            name="Laptops",
            slug="laptops",
            description="Laptop computers",
        )
        db.add(category)
        db.flush()

        # 5. Create product
        product = Product(
            seller_id=seller.id,
            category_id=category.id,
            name="NEXORA Pro Laptop",
            slug="nexora-pro-laptop",
            description="Development test product",
            base_price=Decimal("1299.99"),
        )
        db.add(product)
        db.flush()

        # 6. Create product variant
        variant = ProductVariant(
            product_id=product.id,
            sku="NEXORA-PRO-16-512",
            price=Decimal("1399.99"),
            attributes={
                "color": "Silver",
                "ram": "16GB",
                "storage": "512GB",
            },
        )
        db.add(variant)
        db.flush()

        # 7. Create inventory
        inventory = Inventory(
            variant_id=variant.id,
            quantity=25,
            reserved_quantity=3,
            reorder_level=5,
        )
        db.add(inventory)

        db.commit()

        print("Test data created successfully")
        print(f"User:      {user.id}")
        print(f"Seller:    {seller.id}")
        print(f"Category:  {category.id}")
        print(f"Product:   {product.id}")
        print(f"Variant:   {variant.id}")
        print(f"Inventory: {inventory.id}")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    seed_test_data()