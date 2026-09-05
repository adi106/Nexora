"""rename order shipping country field

Revision ID: 385e106f1959
Revises: 03dbe907688c
Create Date: 2026-09-05 21:08:00

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "385e106f1959"
down_revision: Union[str, Sequence[str], None] = "03dbe907688c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.alter_column(
        "orders",
        "shipping_country",
        new_column_name="shipping_country_code",
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.alter_column(
        "orders",
        "shipping_country_code",
        new_column_name="shipping_country",
    )