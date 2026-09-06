from sqlalchemy.orm import Session

from backend.app.models.category import Category


def get_category_and_descendant_ids(
    category: Category,
    db: Session,
) -> list[int]:
    category_ids = [category.id]
    pending_ids = [category.id]

    while pending_ids:
        child_ids = [
            child.id
            for child in (
                db.query(Category)
                .filter(
                    Category.parent_id.in_(pending_ids),
                    Category.is_active.is_(True),
                )
                .all()
            )
        ]

        category_ids.extend(child_ids)
        pending_ids = child_ids

    return category_ids