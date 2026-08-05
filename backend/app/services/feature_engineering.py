"""
Automated feature engineering for the sales forecasting pipeline.

Turns a raw daily/transactional sales table into a supervised-learning
ready feature matrix: calendar features, lag features, rolling statistics,
and trend indicators.
"""
from typing import List, Tuple

import numpy as np
import pandas as pd


def aggregate_daily_revenue(df: pd.DataFrame) -> pd.DataFrame:
    """Collapse transaction-level rows into one row per calendar day."""
    daily = (
        df.groupby("order_date", as_index=False)
        .agg(revenue=("revenue", "sum"), quantity=("quantity", "sum"))
        .sort_values("order_date")
    )
    daily["order_date"] = pd.to_datetime(daily["order_date"])

    # Fill missing calendar days with 0 so lag/rolling features are correct
    full_range = pd.date_range(daily["order_date"].min(), daily["order_date"].max(), freq="D")
    daily = daily.set_index("order_date").reindex(full_range).fillna(0.0)
    daily.index.name = "order_date"
    daily = daily.reset_index()
    return daily


def build_features(daily: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    """
    Adds calendar, lag, and rolling-window features.
    Returns (dataframe_with_features, feature_column_names).
    """
    df = daily.copy()

    # --- Calendar features ---
    df["day_of_week"] = df["order_date"].dt.dayofweek
    df["day_of_month"] = df["order_date"].dt.day
    df["month"] = df["order_date"].dt.month
    df["quarter"] = df["order_date"].dt.quarter
    df["year"] = df["order_date"].dt.year
    df["week_of_year"] = df["order_date"].dt.isocalendar().week.astype(int)
    df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)
    df["is_month_start"] = df["order_date"].dt.is_month_start.astype(int)
    df["is_month_end"] = df["order_date"].dt.is_month_end.astype(int)

    # --- Lag features (yesterday, last week, last month) ---
    for lag in [1, 2, 3, 7, 14, 30]:
        df[f"revenue_lag_{lag}"] = df["revenue"].shift(lag)

    # --- Rolling window statistics ---
    for window in [7, 14, 30]:
        df[f"revenue_roll_mean_{window}"] = df["revenue"].shift(1).rolling(window).mean()
        df[f"revenue_roll_std_{window}"] = df["revenue"].shift(1).rolling(window).std()

    # --- Trend feature: linear time index ---
    df["time_index"] = np.arange(len(df))

    feature_cols = [c for c in df.columns if c not in ("order_date", "revenue", "quantity")]

    # Drop warm-up rows that don't have enough history for lag/rolling features
    df = df.dropna(subset=[c for c in feature_cols if "lag" in c or "roll" in c])

    return df, feature_cols
