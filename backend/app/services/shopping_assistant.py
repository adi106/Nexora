import anthropic
from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.models.category import Category
from backend.app.models.product import Product
from backend.app.models.review import Review
from backend.app.services.recommendations import get_popular_products

ASSISTANT_MODEL = "claude-opus-5"

SYSTEM_PROMPT_TEMPLATE = """You are the NEXORA shopping assistant, embedded in the NEXORA e-commerce site.

Answer the shopper's question using ONLY the catalog information below - do not invent \
products, prices, or stock that aren't listed. If nothing in the catalog fits, say so \
plainly and suggest they browse or search instead of guessing. Keep answers short \
(2-4 sentences) and conversational, and mention specific product names from the \
catalog when recommending something.

Catalog (may be a partial, relevant slice of NEXORA's full inventory):
{catalog}
"""


class AssistantNotConfigured(Exception):
    pass


def _retrieve_relevant_products(db: Session, query: str, limit: int = 6) -> list[Product]:
    """
    Lightweight retrieval step for the RAG-lite assistant: find active
    products whose name or description match tokens from the shopper's
    question, falling back to overall popularity if nothing matches.
    """

    tokens = [token for token in query.split() if len(token) > 2][:8]

    products: list[Product] = []

    if tokens:
        base_query = db.query(Product).join(Category, Product.category_id == Category.id).filter(
            Product.is_active.is_(True),
            Category.is_active.is_(True),
        )

        name_matches = or_(*[Product.name.ilike(f"%{token}%") for token in tokens])
        products = (
            base_query.filter(name_matches)
            .order_by(Product.created_at.desc())
            .limit(limit)
            .all()
        )

        if len(products) < limit:
            seen_ids = {p.id for p in products}
            description_matches = or_(
                *[Product.description.ilike(f"%{token}%") for token in tokens]
            )
            remaining = (
                base_query.filter(description_matches)
                .order_by(Product.created_at.desc())
                .limit(limit - len(products))
                .all()
            )
            products += [p for p in remaining if p.id not in seen_ids]

    if not products:
        products = get_popular_products(db, limit=limit)

    return products


def _format_catalog_context(db: Session, products: list[Product]) -> str:
    if not products:
        return "(No matching products found in the catalog.)"

    lines = []
    for product in products:
        rating_row = (
            db.query(Review.rating)
            .filter(Review.product_id == product.id)
            .all()
        )
        ratings = [r for (r,) in rating_row]
        avg_rating = f"{sum(ratings) / len(ratings):.1f}/5 ({len(ratings)} reviews)" if ratings else "no reviews yet"

        lines.append(
            f"- {product.name} — ${product.base_price} — {avg_rating}\n"
            f"  {product.description or 'No description available.'}"
        )

    return "\n".join(lines)


def ask_shopping_assistant(
    db: Session,
    message: str,
    history: list[dict] | None = None,
) -> tuple[str, list[Product]]:
    """
    Answer a shopper's question, grounded in a retrieved slice of the
    live NEXORA product catalog (name, price, description, review
    average). Returns the assistant's reply and the products used as
    context, so the caller can show "based on" references.

    Raises AssistantNotConfigured if no Anthropic API key is set.
    """

    if not settings.anthropic_api_key:
        raise AssistantNotConfigured(
            "The AI shopping assistant is not configured. Set ANTHROPIC_API_KEY "
            "on the backend to enable it."
        )

    products = _retrieve_relevant_products(db, message)
    catalog_context = _format_catalog_context(db, products)

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    messages = list(history or [])
    messages.append({"role": "user", "content": message})

    response = client.messages.create(
        model=ASSISTANT_MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT_TEMPLATE.format(catalog=catalog_context),
        messages=messages,
        output_config={"effort": "low"},
    )

    reply = "".join(block.text for block in response.content if block.type == "text")

    return reply, products
