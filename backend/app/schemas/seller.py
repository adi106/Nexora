import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class SellerCreate(BaseModel):
    store_name: str = Field(min_length=1, max_length=150)
    store_slug: str = Field(min_length=1, max_length=150)
    description: str | None = None


class SellerResponse(BaseModel):
    id: int
    user_id: uuid.UUID
    store_name: str
    store_slug: str
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SellerStatsResponse(BaseModel):
    total_revenue: Decimal
    order_count: int
    product_count: int
    customer_count: int
