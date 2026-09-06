import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class InventoryUpdate(BaseModel):
    quantity: int = Field(ge=0)
    reorder_level: int = Field(ge=0)


class InventoryStatusUpdate(BaseModel):
    is_active: bool


class InventoryResponse(BaseModel):
    id: uuid.UUID
    variant_id: uuid.UUID
    quantity: int
    reserved_quantity: int
    reorder_level: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)