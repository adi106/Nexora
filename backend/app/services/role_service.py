import uuid

from sqlalchemy.orm import Session

from backend.app.models.role import Role
from backend.app.models.user_role import UserRole


def get_role_names(db: Session, user_id: uuid.UUID) -> list[str]:
    return [
        name
        for (name,) in db.query(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .filter(UserRole.user_id == user_id)
        .all()
    ]
