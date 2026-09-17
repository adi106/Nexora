from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class DailyMetric(BaseModel):
    date: date
    order_count: int
    revenue: Decimal


class AnalyticsOverviewResponse(BaseModel):
    period_days: int
    revenue_in_period: Decimal
    orders_in_period: int
    new_users_in_period: int
    new_sellers_in_period: int
    daily: list[DailyMetric]


class TopProduct(BaseModel):
    product_id: UUID
    name: str
    units_sold: int
    revenue: Decimal


class CategoryPerformance(BaseModel):
    category_id: int
    name: str
    revenue: Decimal
    order_count: int
