"""add performance indexes

Revision ID: 808bb5b1d277
Revises: ee8c14141d77
Create Date: 2026-09-17 09:46:30.677037

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '808bb5b1d277'
down_revision: Union[str, Sequence[str], None] = 'ee8c14141d77'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index(op.f('ix_products_is_active'), 'products', ['is_active'], unique=False)
    op.create_index(op.f('ix_product_variants_is_active'), 'product_variants', ['is_active'], unique=False)
    op.create_index(op.f('ix_categories_is_active'), 'categories', ['is_active'], unique=False)
    op.create_index(op.f('ix_sellers_is_active'), 'sellers', ['is_active'], unique=False)
    op.create_index(op.f('ix_inventory_is_active'), 'inventory', ['is_active'], unique=False)
    op.create_index(op.f('ix_orders_status'), 'orders', ['status'], unique=False)
    op.create_index(op.f('ix_orders_created_at'), 'orders', ['created_at'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_orders_created_at'), table_name='orders')
    op.drop_index(op.f('ix_orders_status'), table_name='orders')
    op.drop_index(op.f('ix_inventory_is_active'), table_name='inventory')
    op.drop_index(op.f('ix_sellers_is_active'), table_name='sellers')
    op.drop_index(op.f('ix_categories_is_active'), table_name='categories')
    op.drop_index(op.f('ix_product_variants_is_active'), table_name='product_variants')
    op.drop_index(op.f('ix_products_is_active'), table_name='products')
