from uuid import UUID

from pydantic import BaseModel

from backend.app.models.product_interaction import ProductInteractionType


class ProductInteractionCreate(BaseModel):
    product_id: UUID
    interaction_type: ProductInteractionType


class ProductInteractionResponse(BaseModel):
    id: UUID
    user_id: UUID
    product_id: UUID
    interaction_type: ProductInteractionType

    model_config = {
        "from_attributes": True,
    }