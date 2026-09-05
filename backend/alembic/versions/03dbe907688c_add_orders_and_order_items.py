"""add orders and order items

Revision ID: 03dbe907688c
Revises: 82edf67b72d8
Create Date: 2026-09-05 20:47:43.909725

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "03dbe907688c"
down_revision: Union[str, Sequence[str], None] = "82edf67b72d8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.create_table(
        "orders",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING",
                "PAID",
                "SHIPPED",
                "DELIVERED",
                "CANCELLED",
                name="order_status",
            ),
            nullable=False,
        ),
        sa.Column(
            "total_amount",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
        ),
        sa.Column(
            "shipping_full_name",
            sa.String(length=200),
            nullable=False,
        ),
        sa.Column(
            "shipping_address_line1",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "shipping_address_line2",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "shipping_city",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "shipping_region",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column(
            "shipping_postal_code",
            sa.String(length=20),
            nullable=False,
        ),
        sa.Column(
            "shipping_country",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_orders_user_id"),
        "orders",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "order_items",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("order_id", sa.UUID(), nullable=False),
        sa.Column("variant_id", sa.UUID(), nullable=True),
        sa.Column(
            "product_name",
            sa.String(length=200),
            nullable=False,
        ),
        sa.Column(
            "sku",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "unit_price",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
        ),
        sa.Column(
            "quantity",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "subtotal",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["orders.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["variant_id"],
            ["product_variants.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_order_items_order_id"),
        "order_items",
        ["order_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_order_items_variant_id"),
        "order_items",
        ["variant_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_index(
        op.f("ix_order_items_variant_id"),
        table_name="order_items",
    )

    op.drop_index(
        op.f("ix_order_items_order_id"),
        table_name="order_items",
    )

    op.drop_table("order_items")

    op.drop_index(
        op.f("ix_orders_user_id"),
        table_name="orders",
    )

    op.drop_table("orders")

    # The existing carts active-user index is intentionally preserved.