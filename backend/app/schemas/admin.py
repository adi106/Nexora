from decimal import Decimal

from pydantic import BaseModel

from backend.app.schemas.seller import SellerResponse
from backend.app.schemas.user import UserResponse


class AdminStatsResponse(BaseModel):
    user_count: int
    seller_count: int
    product_count: int
    order_count: int
    total_revenue: Decimal


class UserListResponse(BaseModel):
    items: list[UserResponse]
    total: int
    page: int
    page_size: int


class SellerListResponse(BaseModel):
    items: list[SellerResponse]
    total: int
    page: int
    page_size: int


class UserStatusUpdate(BaseModel):
    is_active: bool
