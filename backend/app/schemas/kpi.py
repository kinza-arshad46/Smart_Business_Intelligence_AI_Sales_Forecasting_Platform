from typing import List, Optional, Dict
from pydantic import BaseModel


class KPISummary(BaseModel):
    total_revenue: float
    total_units_sold: float
    average_order_value: float
    total_orders: int
    revenue_growth_mom_pct: Optional[float]
    revenue_growth_yoy_pct: Optional[float]
    average_daily_revenue: float
    top_product: Optional[str]
    top_category: Optional[str]
    top_region: Optional[str]
    forecast_accuracy_pct: Optional[float]
    sales_target_achievement_pct: Optional[float] = None


class TrendPoint(BaseModel):
    period: str
    revenue: float
    units: float


class BreakdownItem(BaseModel):
    label: str
    revenue: float
    units: float
    share_pct: float


class DashboardData(BaseModel):
    kpis: KPISummary
    revenue_trend: List[TrendPoint]
    by_category: List[BreakdownItem]
    by_region: List[BreakdownItem]
    by_product: List[BreakdownItem]
