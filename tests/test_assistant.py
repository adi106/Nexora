from unittest.mock import MagicMock, patch

import anthropic
import httpx2
import pytest
from sqlalchemy import select

from backend.app.models import Category, Product, Seller
from backend.app.services.shopping_assistant import (
    AssistantNotConfigured,
    _retrieve_relevant_products,
    ask_shopping_assistant,
)


TEST_PASSWORD = "TestPassword123!"
BUYER_EMAIL = "secure.test@nexora.com"


def login(client, email=BUYER_EMAIL):
    response = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": TEST_PASSWORD},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def _fake_error_response(status_code: int, error_type: str):
    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    return httpx2.Response(
        status_code,
        request=request,
        json={"type": "error", "error": {"type": error_type, "message": "boom"}},
    )


def test_retrieve_relevant_products_matches_name(test_db):
    seller = test_db.scalar(select(Seller).where(Seller.store_slug == "nexora-test-store"))
    category = test_db.scalar(select(Category).where(Category.slug == "laptops"))
    product = test_db.scalar(select(Product).where(Product.slug == "nexora-pro-laptop"))

    assert seller is not None and category is not None and product is not None

    results = _retrieve_relevant_products(test_db, "Tell me about the NEXORA Pro laptop")

    assert any(p.id == product.id for p in results)


def test_retrieve_relevant_products_falls_back_to_popular(test_db):
    results = _retrieve_relevant_products(test_db, "zzz_no_such_token_zzz")
    assert isinstance(results, list)


def test_chat_endpoint_requires_authentication(client):
    response = client.post("/api/v1/assistant/chat", json={"message": "hi"})
    assert response.status_code == 401


def test_chat_endpoint_returns_503_when_unconfigured(client):
    token = login(client)

    response = client.post(
        "/api/v1/assistant/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "What laptops do you have?"},
    )

    assert response.status_code == 503


def test_ask_shopping_assistant_raises_when_unconfigured(test_db):
    with patch("backend.app.services.shopping_assistant.settings") as mock_settings:
        mock_settings.anthropic_api_key = None
        with pytest.raises(AssistantNotConfigured):
            ask_shopping_assistant(test_db, "hello")


def test_ask_shopping_assistant_calls_anthropic_and_parses_reply(test_db):
    fake_text_block = MagicMock()
    fake_text_block.type = "text"
    fake_text_block.text = "The NEXORA Pro Laptop is a great pick."

    fake_response = MagicMock()
    fake_response.content = [fake_text_block]

    with patch("backend.app.services.shopping_assistant.settings") as mock_settings, patch(
        "backend.app.services.shopping_assistant.anthropic.Anthropic"
    ) as mock_client_cls:
        mock_settings.anthropic_api_key = "sk-ant-fake-key"
        mock_client = MagicMock()
        mock_client.messages.create.return_value = fake_response
        mock_client_cls.return_value = mock_client

        reply, products = ask_shopping_assistant(test_db, "What laptops do you have?")

    assert reply == "The NEXORA Pro Laptop is a great pick."
    assert isinstance(products, list)
    mock_client.messages.create.assert_called_once()
    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs["model"] == "claude-opus-5"
    assert call_kwargs["messages"][-1] == {
        "role": "user",
        "content": "What laptops do you have?",
    }


def test_chat_endpoint_maps_authentication_error(client, test_db):
    token = login(client)
    error = anthropic.AuthenticationError(
        "invalid api key", response=_fake_error_response(401, "authentication_error"), body=None
    )

    with patch(
        "backend.app.api.v1.assistant.ask_shopping_assistant",
        side_effect=error,
    ):
        response = client.post(
            "/api/v1/assistant/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"message": "hi"},
        )

    assert response.status_code == 503


def test_chat_endpoint_maps_rate_limit_error(client, test_db):
    token = login(client)
    error = anthropic.RateLimitError(
        "slow down", response=_fake_error_response(429, "rate_limit_error"), body=None
    )

    with patch(
        "backend.app.api.v1.assistant.ask_shopping_assistant",
        side_effect=error,
    ):
        response = client.post(
            "/api/v1/assistant/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"message": "hi"},
        )

    assert response.status_code == 429


def test_chat_endpoint_returns_referenced_product_ids(client, test_db):
    token = login(client)
    product = test_db.scalar(select(Product).where(Product.slug == "nexora-pro-laptop"))

    with patch(
        "backend.app.api.v1.assistant.ask_shopping_assistant",
        return_value=("Try the NEXORA Pro Laptop.", [product]),
    ):
        response = client.post(
            "/api/v1/assistant/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"message": "hi"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["reply"] == "Try the NEXORA Pro Laptop."
    assert data["referenced_product_ids"] == [str(product.id)]
