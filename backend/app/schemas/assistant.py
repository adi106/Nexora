import uuid

from pydantic import BaseModel, Field


class AssistantMessage(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str


class AssistantChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    history: list[AssistantMessage] = Field(default_factory=list, max_length=20)


class AssistantChatResponse(BaseModel):
    reply: str
    referenced_product_ids: list[uuid.UUID]
