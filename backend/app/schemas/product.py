import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ProductBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    slug: str = Field(min_length=1, max_length=200)
    description: str | None = None
    base_price: Decimal = Field(gt=0)


class ProductCreate(ProductBase):
    category_id: int


class ProductResponse(ProductBase):
    id: uuid.UUID
    seller_id: int
    category_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)