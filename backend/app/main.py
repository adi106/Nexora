from fastapi import FastAPI

from backend.app.api.v1.auth import router as auth_router
from backend.app.api.v1.cart import router as cart_router
from backend.app.api.v1.categories import router as categories_router
from backend.app.api.v1.health import router as health_router
from backend.app.api.v1.orders import router as orders_router
from backend.app.api.v1.products import router as products_router
from backend.app.api.v1.users import router as users_router


app = FastAPI(
    title="NEXORA API",
    description="AI-powered e-commerce platform",
    version="0.1.0",
)


app.include_router(
    health_router,
    prefix="/api/v1",
)

app.include_router(
    users_router,
    prefix="/api/v1",
)

app.include_router(
    auth_router,
    prefix="/api/v1",
)

app.include_router(
    products_router,
    prefix="/api/v1",
)

app.include_router(
    categories_router,
    prefix="/api/v1",
)

app.include_router(
    cart_router,
    prefix="/api/v1",
)

app.include_router(
    orders_router,
    prefix="/api/v1",
)