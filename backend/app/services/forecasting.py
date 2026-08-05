"""
Orchestrates the end-to-end forecasting pipeline:
raw sales rows -> daily aggregation -> feature engineering -> train &
compare algorithms -> persist best model -> generate future predictions
with confidence scores.
"""
import uuid
from datetime import datetime, timedelta
from typing import List, Optional

import numpy as np
import pandas as pd

from app.core.logging_config import logger
from app.ml import trainer as ml_trainer
from app.ml.evaluator import confidence_score_from_mape
from app.ml.model_registry import save_model, load_model
from app.services.feature_engineering import aggregate_daily_revenue, build_features


def prepare_training_data(sales_df: pd.DataFrame):
    daily = aggregate_daily_revenue(sales_df)
    features_df, feature_cols = build_features(daily)
    return daily, features_df, feature_cols


def train_models_for_dataset(
    dataset_id: int,
    sales_df: pd.DataFrame,
    algorithms: List[str],
    test_size: float = 0.2,
    tune: bool = False,
) -> List[dict]:
    """
    Returns a list of dicts ready to be persisted as MLModel rows, e.g.:
        {algorithm, version, file_path, mae, rmse, mape, r2, hyperparameters, is_active}
    """
    if len(sales_df) < 15:
        raise ValueError(
            "Not enough historical data to train a model. "
            "Please upload at least 15 days of sales history."
        )

    daily, features_df, feature_cols = prepare_training_data(sales_df)

    if len(features_df) < 5:
        raise ValueError(
            "Not enough usable rows after feature engineering "
            "(need roughly 40+ days of history for reliable lag/rolling features)."
        )

    results = ml_trainer.train_and_compare(
        daily=daily, features_df=features_df, feature_cols=feature_cols,
        algorithms=algorithms, test_size=test_size, tune=tune,
    )
    best = ml_trainer.pick_best(results)

    version = datetime.utcnow().strftime("%Y%m%d%H%M%S") + "_" + uuid.uuid4().hex[:6]
    persisted = []

    for r in results:
        meta = {
            "algorithm": r["algorithm"],
            "kind": r["kind"],
            "feature_cols": feature_cols,
            "params": r["params"],
            "metrics": r["metrics"],
            "trained_at": datetime.utcnow().isoformat(),
        }
        file_path = save_model(dataset_id, r["algorithm"], version, r["model"], meta)
        persisted.append({
            "algorithm": r["algorithm"],
            "version": version,
            "file_path": file_path,
            "mae": r["metrics"].get("mae"),
            "rmse": r["metrics"].get("rmse"),
            "mape": r["metrics"].get("mape"),
            "r2": r["metrics"].get("r2"),
            "hyperparameters": r["params"],
            "is_active": r["algorithm"] == best["algorithm"],
        })

    logger.info(f"Best algorithm for dataset {dataset_id}: {best['algorithm']} "
                f"(MAE={best['metrics']['mae']:.2f})")
    return persisted


def _forecast_tree_model(model, daily: pd.DataFrame, feature_cols: List[str], horizon_days: int) -> pd.DataFrame:
    """
    Recursive multi-step forecasting for sklearn/xgboost/lightgbm models:
    predict one day, append it to history, recompute features, repeat.
    """
    history = daily.copy()
    future_rows = []

    for step in range(horizon_days):
        next_date = history["order_date"].max() + timedelta(days=1)
        temp = pd.concat([
            history,
            pd.DataFrame([{"order_date": next_date, "revenue": np.nan, "quantity": np.nan}])
        ], ignore_index=True)

        # Rebuild features on the extended history to correctly compute lags/rolling stats
        from app.services.feature_engineering import build_features
        temp_filled = temp.copy()
        temp_filled["revenue"] = temp_filled["revenue"].ffill()
        temp_filled["quantity"] = temp_filled["quantity"].ffill()
        feats, _ = build_features(temp_filled)

        last_row = feats.iloc[[-1]]
        X_next = last_row[feature_cols].values
        y_next = float(model.predict(X_next)[0])
        y_next = max(y_next, 0.0)

        history = pd.concat([
            history,
            pd.DataFrame([{"order_date": next_date, "revenue": y_next, "quantity": 0.0}])
        ], ignore_index=True)

        future_rows.append({"date": next_date, "predicted_revenue": y_next})

    return pd.DataFrame(future_rows)


def _forecast_prophet_model(model, horizon_days: int) -> pd.DataFrame:
    future = model.make_future_dataframe(periods=horizon_days, freq="D")
    forecast = model.predict(future)
    tail = forecast.tail(horizon_days)
    return pd.DataFrame({
        "date": tail["ds"].values,
        "predicted_revenue": tail["yhat"].clip(lower=0).values,
        "lower_bound": tail["yhat_lower"].clip(lower=0).values,
        "upper_bound": tail["yhat_upper"].clip(lower=0).values,
    })


def generate_forecast(
    ml_model_row,
    sales_df: pd.DataFrame,
    horizon_days: int,
) -> pd.DataFrame:
    """
    Loads the persisted model referenced by `ml_model_row` (an MLModel ORM
    object) and produces a forecast dataframe with columns:
    date, predicted_revenue, lower_bound, upper_bound, confidence_score
    """
    model_obj, meta = load_model(ml_model_row.file_path)
    daily = aggregate_daily_revenue(sales_df)
    mape = ml_model_row.mape
    confidence = confidence_score_from_mape(mape)

    if meta.get("kind") == "prophet" or ml_model_row.algorithm == "prophet":
        fc = _forecast_prophet_model(model_obj, horizon_days)
        fc["confidence_score"] = confidence
    else:
        feature_cols = meta.get("feature_cols", [])
        fc = _forecast_tree_model(model_obj, daily, feature_cols, horizon_days)
        # Simple uncertainty band derived from historical RMSE, widening with horizon
        rmse = ml_model_row.rmse or (fc["predicted_revenue"].std() or 1.0)
        step = np.arange(1, len(fc) + 1)
        band = rmse * np.sqrt(step)
        fc["lower_bound"] = (fc["predicted_revenue"] - band).clip(lower=0)
        fc["upper_bound"] = fc["predicted_revenue"] + band
        fc["confidence_score"] = confidence

    return fc
