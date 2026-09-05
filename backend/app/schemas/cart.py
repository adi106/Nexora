import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CartItemCreate(BaseModel):
    variant_id: uuid.UUID
    quantity: int = Field(gt=0)


class CartItemUpdate(BaseModel):
    quantity: int = Field(gt=0)


class CartItemResponse(BaseModel):
    id: uuid.UUID
    cart_id: uuid.UUID
    variant_id: uuid.UUID
    quantity: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CartResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    status: str
    created_at: datetime
    updated_at: datetime
    items: list[CartItemResponse] = []

    model_config = ConfigDict(from_attributes=True)