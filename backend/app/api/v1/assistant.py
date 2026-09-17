import anthropic
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.security import get_current_user
from backend.app.db.dependencies import get_db
from backend.app.models.user import User
from backend.app.schemas.assistant import AssistantChatRequest, AssistantChatResponse
from backend.app.services.shopping_assistant import AssistantNotConfigured, ask_shopping_assistant

router = APIRouter(prefix="/assistant", tags=["Assistant"])


@router.post("/chat", response_model=AssistantChatResponse)
def chat_with_assistant(
    chat_request: AssistantChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        reply, referenced_products = ask_shopping_assistant(
            db,
            chat_request.message,
            history=[m.model_dump() for m in chat_request.history],
        )
    except AssistantNotConfigured as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    except anthropic.AuthenticationError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The AI shopping assistant is misconfigured (invalid API key).",
        )
    except anthropic.RateLimitError:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="The AI shopping assistant is receiving too many requests. Please try again shortly.",
        )
    except (anthropic.APIStatusError, anthropic.APIConnectionError):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI shopping assistant is temporarily unavailable. Please try again shortly.",
        )

    return AssistantChatResponse(
        reply=reply,
        referenced_product_ids=[product.id for product in referenced_products],
    )
