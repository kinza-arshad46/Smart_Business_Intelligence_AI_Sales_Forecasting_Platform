"""
Handles CSV/Excel ingestion: flexible column detection, validation,
cleaning, and loading into the SalesRecord table.

Designed to be forgiving about real-world messy business data:
- Accepts many common header name variants (date/order date/invoice date, etc.)
- Coerces types, drops unusable rows, fills safe defaults
- Produces a structured validation report the user can inspect
"""
import json
from datetime import datetime
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

from app.core.logging_config import logger

# Maps canonical field -> list of acceptable source header keywords (lowercased)
COLUMN_ALIASES: Dict[str, List[str]] = {
    "order_date": ["date", "order date", "order_date", "invoice date", "sale date", "transaction date", "orderdate", "time", "timestamp"],
    "product": ["product", "product name", "item", "item name", "sku", "product_name", "title"],
    "category": ["category", "product category", "segment", "product_category", "type", "dept", "department"],
    "region": ["region", "state", "country", "location", "market", "territory", "city"],
    "quantity": ["quantity", "qty", "units", "units sold", "quantity sold", "items_sold", "count"],
    "unit_price": ["unit price", "price", "unit_price", "price per unit", "rate", "cost_per_unit"],
    "revenue": ["revenue", "sales", "total sales", "amount", "total amount", "total", "sales amount", "grand total", "total_price", "price_total"],
    "cost": ["cost", "unit cost", "cogs", "total cost", "expense"],
}

REQUIRED_FIELDS = ["order_date"]  # Date is essential for forecasting


def _normalize_columns(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, str]]:
    """Rename source columns to canonical names using smart keyword matching."""
    lower_map = {c: str(c).strip().lower().replace("-", "_").replace(" ", "_") for c in df.columns}
    detected: Dict[str, str] = {}
    used_originals = set()

    # 1. Broad matching using keywords
    for canonical, aliases in COLUMN_ALIASES.items():
        for original, lowered in lower_map.items():
            if original in used_originals:
                continue
            
            # Check for exact match or keyword inclusion
            if any(alias in lowered for alias in aliases):
                detected[canonical] = original
                used_originals.add(original)
                break

    rename_map = {source: canonical for canonical, source in detected.items()}
    df = df.rename(columns=rename_map)
    return df, detected


def read_upload_file(file_path: str) -> pd.DataFrame:
    if file_path.lower().endswith(".csv"):
        return pd.read_csv(file_path)
    return pd.read_excel(file_path)


def validate_and_clean(df: pd.DataFrame) -> Tuple[pd.DataFrame, dict]:
    """
    Returns (clean_dataframe, validation_report_dict).
    Cleans messy data, handles auto-fallbacks for missing revenue/quantities.
    """
    warnings: List[str] = []
    errors: List[str] = []
    total_rows = len(df)

    # Normalize headers
    df, detected = _normalize_columns(df)

    # Dynamic Fallback 1: Date Column Auto-Detect if missing
    if "order_date" not in df.columns:
        for col in df.columns:
            if "date" in str(col).lower() or "time" in str(col).lower():
                df = df.rename(columns={col: "order_date"})
                detected["order_date"] = col
                break

    missing_required = [f for f in REQUIRED_FIELDS if f not in df.columns]
    if missing_required:
        errors.append(
            f"Missing required column(s): {missing_required}. "
            f"Please ensure dataset includes a Date column."
        )
        report = {
            "is_valid": False,
            "total_rows": total_rows,
            "valid_rows": 0,
            "invalid_rows": total_rows,
            "missing_columns": missing_required,
            "detected_columns": detected,
            "warnings": warnings,
            "errors": errors,
        }
        return pd.DataFrame(), report

    # Ensure optional columns exist
    for col in ["product", "category", "region", "quantity", "unit_price", "revenue", "cost"]:
        if col not in df.columns:
            df[col] = np.nan

    # --- Type Coercion ---
    df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")
    before = len(df)
    df = df.dropna(subset=["order_date"])
    dropped_dates = before - len(df)
    if dropped_dates:
        warnings.append(f"Dropped {dropped_dates} row(s) with unparseable dates.")

    for col in ["quantity", "unit_price", "revenue", "cost"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # --- SMART REVENUE & QUANTITY CALCULATION FALLBACKS ---
    # 1. Derive revenue if quantity & unit_price exist
    needs_revenue = df["revenue"].isna() & (df["quantity"] > 0) & (df["unit_price"] > 0)
    df.loc[needs_revenue, "revenue"] = df.loc[needs_revenue, "quantity"] * df.loc[needs_revenue, "unit_price"]

    # 2. Dynamic Fallback: If revenue is STILL missing/all NaN, pick first available numeric column!
    if df["revenue"].isna().all() or (df["revenue"] == 0).all():
        numeric_cols = df.select_dtypes(include=[np.number]).columns.difference(["quantity", "unit_price", "cost"])
        if len(numeric_cols) > 0:
            target_col = numeric_cols[0]
            df["revenue"] = df[target_col]
            warnings.append(f"Revenue auto-mapped from numeric column '{target_col}'.")

    # Final safe fills
    df["quantity"] = df["quantity"].fillna(1)
    df["unit_price"] = df["unit_price"].fillna(df["revenue"])
    df["revenue"] = df["revenue"].fillna(0)

    # Clean rows with negative revenue
    before = len(df)
    df = df[df["revenue"] >= 0]
    dropped_negative = before - len(df)
    if dropped_negative:
        warnings.append(f"Dropped {dropped_negative} row(s) with negative revenue.")

    # Fill metadata text columns
    df["product"] = df["product"].fillna("Unknown Product").astype(str)
    df["category"] = df["category"].fillna("Uncategorized").astype(str)
    df["region"] = df["region"].fillna("Unknown Region").astype(str)

    valid_rows = len(df)
    invalid_rows = total_rows - valid_rows

    if valid_rows == 0:
        errors.append("No valid rows remained after cleaning.")

    report = {
        "is_valid": valid_rows > 0,
        "total_rows": total_rows,
        "valid_rows": valid_rows,
        "invalid_rows": invalid_rows,
        "missing_columns": [],
        "detected_columns": detected,
        "warnings": warnings,
        "errors": errors,
    }
    logger.info(f"Validated upload: {valid_rows}/{total_rows} rows kept.")
    return df, report


def dataframe_to_records(df: pd.DataFrame, dataset_id: int) -> List[dict]:
    records = []
    for _, row in df.iterrows():
        records.append({
            "dataset_id": dataset_id,
            "order_date": row["order_date"].date(),
            "product": row["product"],
            "category": row["category"],
            "region": row["region"],
            "quantity": float(row["quantity"]),
            "unit_price": float(row["unit_price"]),
            "revenue": float(row["revenue"]),
            "cost": float(row["cost"]) if pd.notna(row.get("cost")) else None,
        })
    return records