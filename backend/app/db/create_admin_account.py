from backend.app.core.security import hash_password
from backend.app.db.session import SessionLocal
from backend.app.models.role import Role
from backend.app.models.user import User
from backend.app.models.user_role import UserRole


db = SessionLocal()

try:
    user = User(
        email="admin.test@nexora.com",
        password_hash=hash_password("AdminPassword123!"),
        first_name="NEXORA",
        last_name="Admin",
    )

    db.add(user)
    db.flush()

    role = (
        db.query(Role)
        .filter(Role.name == "admin")
        .first()
    )

    if role is None:
        raise RuntimeError("Admin role not found")

    db.add(
        UserRole(
            user_id=user.id,
            role_id=role.id,
        )
    )

    db.commit()

    print("Admin created:", user.email)
    print("Role:", role.name)

finally:
    db.close()