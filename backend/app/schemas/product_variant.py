import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ProductVariantCreate(BaseModel):
    sku: str = Field(min_length=1, max_length=100)
    price: Decimal = Field(gt=0)
    attributes: dict = Field(default_factory=dict)


class ProductVariantUpdate(BaseModel):
    sku: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )
    price: Decimal | None = Field(
        default=None,
        gt=0,
    )
    attributes: dict | None = None


class ProductVariantStatusUpdate(BaseModel):
    is_active: bool


class ProductVariantResponse(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    sku: str
    price: Decimal
    attributes: dict
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)