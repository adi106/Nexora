import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AddressCreate(BaseModel):
    address_line1: str = Field(min_length=1, max_length=255)
    address_line2: str | None = Field(default=None, max_length=255)
    city: str = Field(min_length=1, max_length=100)
    region: str | None = Field(default=None, max_length=100)
    postal_code: str = Field(min_length=1, max_length=20)
    country_code: str = Field(min_length=2, max_length=2)
    is_default: bool = False


class AddressUpdate(BaseModel):
    address_line1: str | None = Field(default=None, min_length=1, max_length=255)
    address_line2: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, min_length=1, max_length=100)
    region: str | None = Field(default=None, max_length=100)
    postal_code: str | None = Field(default=None, min_length=1, max_length=20)
    country_code: str | None = Field(default=None, min_length=2, max_length=2)
    is_default: bool | None = None


class AddressResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    address_line1: str
    address_line2: str | None
    city: str
    region: str | None
    postal_code: str
    country_code: str
    is_default: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
