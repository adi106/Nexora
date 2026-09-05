import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class OrderCreate(BaseModel):
    address_id: uuid.UUID


class MockPaymentRequest(BaseModel):
    succeed: bool = True


class OrderStatusUpdate(BaseModel):
    status: str


class OrderItemResponse(BaseModel):
    id: uuid.UUID
    variant_id: uuid.UUID | None
    product_name: str
    sku: str
    unit_price: Decimal
    quantity: int
    subtotal: Decimal

    model_config = ConfigDict(from_attributes=True)


class OrderResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    status: str
    total_amount: Decimal

    shipping_full_name: str
    shipping_address_line1: str
    shipping_address_line2: str | None
    shipping_city: str
    shipping_region: str | None
    shipping_postal_code: str
    shipping_country_code: str

    created_at: datetime
    updated_at: datetime

    items: list[OrderItemResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)