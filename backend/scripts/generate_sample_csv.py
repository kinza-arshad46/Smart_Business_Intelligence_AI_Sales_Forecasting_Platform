"""
Generates a realistic ~2 years of daily sample sales data so you can try
the whole platform (upload -> train -> predict -> dashboard) immediately
without needing your own dataset first.

Usage:
    python scripts/generate_sample_csv.py
Output:
    data/sample/sample_sales.csv
"""
import random
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

random.seed(42)
np.random.seed(42)

PRODUCTS = {
    "Wireless Mouse": "Electronics",
    "Mechanical Keyboard": "Electronics",
    "USB-C Hub": "Electronics",
    "Office Chair": "Furniture",
    "Standing Desk": "Furniture",
    "Desk Lamp": "Furniture",
    "Notebook Set": "Stationery",
    "Ballpoint Pens (Pack)": "Stationery",
    "Sticky Notes": "Stationery",
    "Coffee Mug": "Home & Kitchen",
    "Water Bottle": "Home & Kitchen",
}
REGIONS = ["North", "South", "East", "West", "Central"]

START = date(2024, 1, 1)
END = date(2025, 12, 31)

rows = []
d = START
while d <= END:
    n_orders = np.random.poisson(lam=12)
    # weekday seasonality: weekends slightly lower for B2B-style products
    weekday_factor = 0.7 if d.weekday() >= 5 else 1.0
    # yearly growth trend + a seasonal bump in Nov/Dec (holiday shopping)
    days_since_start = (d - START).days
    trend_factor = 1 + (days_since_start / 730) * 0.5
    season_factor = 1.6 if d.month in (11, 12) else 1.0

    n_orders = max(0, int(n_orders * weekday_factor * trend_factor * season_factor))

    for _ in range(n_orders):
        product = random.choice(list(PRODUCTS.keys()))
        category = PRODUCTS[product]
        region = random.choice(REGIONS)
        quantity = random.randint(1, 8)
        base_price = {
            "Electronics": random.uniform(15, 120),
            "Furniture": random.uniform(60, 350),
            "Stationery": random.uniform(2, 15),
            "Home & Kitchen": random.uniform(8, 30),
        }[category]
        unit_price = round(base_price, 2)
        revenue = round(unit_price * quantity, 2)
        cost = round(revenue * random.uniform(0.5, 0.7), 2)

        rows.append({
            "Order Date": d.isoformat(),
            "Product": product,
            "Category": category,
            "Region": region,
            "Quantity": quantity,
            "Unit Price": unit_price,
            "Revenue": revenue,
            "Cost": cost,
        })
    d += timedelta(days=1)

df = pd.DataFrame(rows)
out_path = Path(__file__).resolve().parent.parent / "data" / "sample" / "sample_sales.csv"
out_path.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(out_path, index=False)
print(f"Generated {len(df)} sample sales rows -> {out_path}")
