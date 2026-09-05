"""Seed system roles

Revision ID: cf027c79c928
Revises: fd3e8a3b533b
Create Date: 2026-09-05
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "cf027c79c928"
down_revision: Union[str, Sequence[str], None] = "fd3e8a3b533b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Seed the default system roles."""

    roles_table = sa.table(
        "roles",
        sa.column("name", sa.String),
    )

    op.bulk_insert(
        roles_table,
        [
            {"name": "customer"},
            {"name": "seller"},
            {"name": "admin"},
        ],
    )


def downgrade() -> None:
    """Remove the default system roles."""

    op.execute(
        sa.text(
            """
            DELETE FROM roles
            WHERE name IN ('customer', 'seller', 'admin')
            """
        )
    )