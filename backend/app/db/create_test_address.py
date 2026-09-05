from backend.app.db.session import SessionLocal
from backend.app.models.address import Address
from backend.app.models.user import User


TEST_EMAIL = "secure.test@nexora.com"


db = SessionLocal()

try:
    user = (
        db.query(User)
        .filter(User.email == TEST_EMAIL)
        .first()
    )

    if user is None:
        raise RuntimeError(f"User not found: {TEST_EMAIL}")

    existing_address = (
        db.query(Address)
        .filter(Address.user_id == user.id)
        .first()
    )

    if existing_address:
        print("Test address already exists:")
        print(existing_address.id)
    else:
        address = Address(
            user_id=user.id,
            address_line1="123 Victoria Street",
            address_line2=None,
            city="Hamilton",
            region="Waikato",
            postal_code="3204",
            country_code="NZ",
            is_default=True,
        )

        db.add(address)
        db.commit()
        db.refresh(address)

        print("Test address created:")
        print("ID:", address.id)
        print("Address:", address.address_line1)
        print("City:", address.city)
        print("Country:", address.country_code)

finally:
    db.close()