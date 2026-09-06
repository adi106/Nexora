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
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ProductStatusUpdate(BaseModel):
    is_active: bool

class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    slug: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    base_price: Decimal | None = Field(default=None, gt=0)
    category_id: int | None = None