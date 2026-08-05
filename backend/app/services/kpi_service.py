"""
Computes the Business Intelligence KPIs shown on the dashboard.

KPIs implemented (as requested in the project scope):
  1. Total Revenue
  2. Total Units Sold
  3. Average Order Value (AOV)
  4. Total Orders (transaction count)
  5. Revenue Growth % - Month over Month (MoM)
  6. Revenue Growth % - Year over Year (YoY)
  7. Average Daily Revenue
  8. Top Performing Product
  9. Top Performing Category
  10. Top Performing Region
  11. Forecast Accuracy % (derived from the active model's MAPE)
  12. Sales Target Achievement % (optional, if a target is supplied)
  13. Revenue trend over time (daily/weekly/monthly series)
  14. Revenue breakdown by Category / Region / Product (with % share)
"""
from typing import List, Optional

import pandas as pd


def _pct_change(current: float, previous: float) -> Optional[float]:
    if previous in (0, None) or pd.isna(previous):
        return None
    return round(((current - previous) / previous) * 100, 2)


def compute_kpis(df: pd.DataFrame, active_model_mape: Optional[float] = None,
                  sales_target: Optional[float] = None) -> dict:
    if df.empty:
        return {
            "total_revenue": 0, "total_units_sold": 0, "average_order_value": 0,
            "total_orders": 0, "revenue_growth_mom_pct": None, "revenue_growth_yoy_pct": None,
            "average_daily_revenue": 0, "top_product": None, "top_category": None,
            "top_region": None, "forecast_accuracy_pct": None, "sales_target_achievement_pct": None,
        }

    df = df.copy()
    df["order_date"] = pd.to_datetime(df["order_date"])

    total_revenue = float(df["revenue"].sum())
    total_units = float(df["quantity"].sum())
    total_orders = int(len(df))
    aov = round(total_revenue / total_orders, 2) if total_orders else 0

    n_days = (df["order_date"].max() - df["order_date"].min()).days + 1
    avg_daily_revenue = round(total_revenue / max(n_days, 1), 2)

    # --- MoM / YoY growth ---
    monthly = df.set_index("order_date").resample("ME")["revenue"].sum()
    mom_growth = None
    if len(monthly) >= 2:
        mom_growth = _pct_change(monthly.iloc[-1], monthly.iloc[-2])

    yearly = df.set_index("order_date").resample("YE")["revenue"].sum()
    yoy_growth = None
    if len(yearly) >= 2:
        yoy_growth = _pct_change(yearly.iloc[-1], yearly.iloc[-2])

    top_product = df.groupby("product")["revenue"].sum().idxmax() if df["product"].notna().any() else None
    top_category = df.groupby("category")["revenue"].sum().idxmax() if df["category"].notna().any() else None
    top_region = df.groupby("region")["revenue"].sum().idxmax() if df["region"].notna().any() else None

    forecast_accuracy = round(max(0.0, 100 - active_model_mape), 2) if active_model_mape is not None else None

    target_achievement = None
    if sales_target:
        target_achievement = round((total_revenue / sales_target) * 100, 2)

    return {
        "total_revenue": round(total_revenue, 2),
        "total_units_sold": round(total_units, 2),
        "average_order_value": aov,
        "total_orders": total_orders,
        "revenue_growth_mom_pct": mom_growth,
        "revenue_growth_yoy_pct": yoy_growth,
        "average_daily_revenue": avg_daily_revenue,
        "top_product": top_product,
        "top_category": top_category,
        "top_region": top_region,
        "forecast_accuracy_pct": forecast_accuracy,
        "sales_target_achievement_pct": target_achievement,
    }


def revenue_trend(df: pd.DataFrame, freq: str = "D") -> List[dict]:
    """freq: 'D' daily, 'W' weekly, 'ME' monthly"""
    if df.empty:
        return []
    df = df.copy()
    df["order_date"] = pd.to_datetime(df["order_date"])
    grouped = df.set_index("order_date").resample(freq).agg(
        revenue=("revenue", "sum"), units=("quantity", "sum")
    ).reset_index()
    grouped["period"] = grouped["order_date"].dt.strftime("%Y-%m-%d")
    return grouped[["period", "revenue", "units"]].to_dict(orient="records")


def breakdown_by(df: pd.DataFrame, column: str) -> List[dict]:
    if df.empty or column not in df.columns:
        return []
    grouped = df.groupby(column).agg(revenue=("revenue", "sum"), units=("quantity", "sum")).reset_index()
    total = grouped["revenue"].sum()
    grouped["share_pct"] = (grouped["revenue"] / total * 100).round(2) if total else 0
    grouped = grouped.sort_values("revenue", ascending=False)
    grouped = grouped.rename(columns={column: "label"})
    return grouped[["label", "revenue", "units", "share_pct"]].to_dict(orient="records")
