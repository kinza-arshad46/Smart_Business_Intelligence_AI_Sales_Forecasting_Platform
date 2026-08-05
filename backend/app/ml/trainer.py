"""
Multi-algorithm sales forecasting trainer.

Supports: XGBoost, LightGBM, Prophet, plus scikit-learn Random Forest and
Gradient Boosting as dependency-free fallbacks. Every algorithm is imported
lazily and wrapped in try/except so the platform runs and trains SOMETHING
useful even in an environment where the optional heavy libraries
(xgboost / lightgbm / prophet) are not installed -- it just skips those and
tells the caller which ones were unavailable, instead of crashing.
"""
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from app.core.logging_config import logger
from app.ml.evaluator import evaluate

AVAILABLE_ALGORITHMS = ["gradient_boosting", "random_forest", "xgboost", "lightgbm", "prophet"]


def _train_sklearn_model(name: str, X_train, y_train, tune: bool):
    from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
    from sklearn.model_selection import RandomizedSearchCV

    if name == "gradient_boosting":
        base = GradientBoostingRegressor(random_state=42)
        param_grid = {
            "n_estimators": [100, 200],
            "max_depth": [2, 3, 4],
            "learning_rate": [0.01, 0.05, 0.1],
        }
    elif name == "random_forest":
        # Force n_jobs=1 to prevent Windows loky/multiprocessing freezes
        base = RandomForestRegressor(random_state=42, n_jobs=1)
        param_grid = {
            "n_estimators": [100, 200],
            "max_depth": [None, 5, 10],
            "min_samples_leaf": [1, 2, 4],
        }
    else:
        raise ValueError(name)

    if tune:
        search = RandomizedSearchCV(
            base, param_grid, n_iter=4, cv=3, random_state=42,
            scoring="neg_mean_absolute_error", n_jobs=1,
        )
        search.fit(X_train, y_train)
        return search.best_estimator_, search.best_params_
    else:
        base.fit(X_train, y_train)
        return base, base.get_params()


def _train_xgboost(X_train, y_train, tune: bool):
    import xgboost as xgb

    params = dict(n_estimators=200, max_depth=4, learning_rate=0.05,
                  subsample=0.9, colsample_bytree=0.9, random_state=42, n_jobs=1)
    if tune:
        from sklearn.model_selection import RandomizedSearchCV
        grid = {
            "n_estimators": [100, 200],
            "max_depth": [3, 4, 6],
            "learning_rate": [0.01, 0.05, 0.1],
        }
        search = RandomizedSearchCV(
            xgb.XGBRegressor(random_state=42, n_jobs=1), grid, n_iter=4, cv=3,
            scoring="neg_mean_absolute_error", n_jobs=1, random_state=42,
        )
        search.fit(X_train, y_train)
        return search.best_estimator_, search.best_params_
    model = xgb.XGBRegressor(**params)
    model.fit(X_train, y_train)
    return model, params


def _train_lightgbm(X_train, y_train, tune: bool):
    import lightgbm as lgb

    # Added n_jobs=1 and verbose=-1 to avoid Windows Loky CPU Core lockups
    params = dict(n_estimators=200, max_depth=-1, learning_rate=0.05, num_leaves=31, random_state=42, n_jobs=1, verbose=-1)
    if tune:
        from sklearn.model_selection import RandomizedSearchCV
        grid = {
            "n_estimators": [100, 200],
            "num_leaves": [15, 31],
            "learning_rate": [0.01, 0.05, 0.1],
        }
        search = RandomizedSearchCV(
            lgb.LGBMRegressor(random_state=42, n_jobs=1, verbose=-1), grid, n_iter=4, cv=3,
            scoring="neg_mean_absolute_error", n_jobs=1, random_state=42,
        )
        search.fit(X_train, y_train)
        return search.best_estimator_, search.best_params_
    model = lgb.LGBMRegressor(**params)
    model.fit(X_train, y_train)
    return model, params


def _train_prophet(daily: pd.DataFrame, test_size: float):
    from prophet import Prophet

    prophet_df = daily.rename(columns={"order_date": "ds", "revenue": "y"})[["ds", "y"]]
    split_idx = int(len(prophet_df) * (1 - test_size))
    train_df, test_df = prophet_df.iloc[:split_idx], prophet_df.iloc[split_idx:]

    model = Prophet(daily_seasonality=False, weekly_seasonality=True, yearly_seasonality=True)
    model.fit(train_df)

    future = model.make_future_dataframe(periods=len(test_df), freq="D")
    forecast = model.predict(future)
    y_pred = forecast.iloc[split_idx:]["yhat"].values
    y_true = test_df["y"].values

    return model, y_true, y_pred, {}


def train_and_compare(
    daily: pd.DataFrame,
    features_df: pd.DataFrame,
    feature_cols: List[str],
    algorithms: List[str],
    test_size: float = 0.2,
    tune: bool = False,
) -> List[dict]:
    """
    Trains every requested (and available) algorithm, evaluates it on a
    held-out chronological test split, and returns a list of result dicts:
        {algorithm, model_obj, metrics, params, predict_fn}
    """
    results: List[dict] = []

    # --- Tree-based / sklearn-style models trained on engineered features ---
    n = len(features_df)
    split_idx = max(int(n * (1 - test_size)), 1)
    
    # Cast arrays to float to prevent object type issues during evaluation
    X = features_df[feature_cols].values.astype(np.float64)
    y = features_df["revenue"].values.astype(np.float64)
    
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]

    if len(X_test) == 0:
        # Fallback split
        X_train, X_test = X[:-1], X[-1:]
        y_train, y_test = y[:-1], y[-1:]

    for algo in algorithms:
        try:
            if algo == "gradient_boosting":
                model, params = _train_sklearn_model("gradient_boosting", X_train, y_train, tune)
                y_pred = model.predict(X_test)
                metrics = evaluate(np.array(y_test, dtype=float), np.array(y_pred, dtype=float))
                results.append({"algorithm": algo, "model": model, "metrics": metrics,
                                 "params": params, "kind": "sklearn"})

            elif algo == "random_forest":
                model, params = _train_sklearn_model("random_forest", X_train, y_train, tune)
                y_pred = model.predict(X_test)
                metrics = evaluate(np.array(y_test, dtype=float), np.array(y_pred, dtype=float))
                results.append({"algorithm": algo, "model": model, "metrics": metrics,
                                 "params": params, "kind": "sklearn"})

            elif algo == "xgboost":
                model, params = _train_xgboost(X_train, y_train, tune)
                y_pred = model.predict(X_test)
                metrics = evaluate(np.array(y_test, dtype=float), np.array(y_pred, dtype=float))
                results.append({"algorithm": algo, "model": model, "metrics": metrics,
                                 "params": params, "kind": "sklearn"})

            elif algo == "lightgbm":
                model, params = _train_lightgbm(X_train, y_train, tune)
                y_pred = model.predict(X_test)
                metrics = evaluate(np.array(y_test, dtype=float), np.array(y_pred, dtype=float))
                results.append({"algorithm": algo, "model": model, "metrics": metrics,
                                 "params": params, "kind": "sklearn"})

            elif algo == "prophet":
                model, y_true_p, y_pred_p, params = _train_prophet(daily, test_size)
                metrics = evaluate(np.array(y_true_p, dtype=float), np.array(y_pred_p, dtype=float))
                results.append({"algorithm": algo, "model": model, "metrics": metrics,
                                 "params": params, "kind": "prophet"})

            else:
                logger.warning(f"Unknown algorithm requested: {algo}, skipping.")
                continue

            logger.info(f"Trained {algo}: {results[-1]['metrics']}")

        except ImportError:
            logger.warning(f"Library for '{algo}' is not installed - skipping.")
        except Exception as e:
            logger.error(f"Training '{algo}' failed: {e}")

    if not results:
        raise RuntimeError(
            "No forecasting model could be trained. This usually means there isn't "
            "enough historical data yet (need at least ~40 days of sales history)."
        )

    return results


def pick_best(results: List[dict]) -> dict:
    """Best model = lowest MAE on the held-out test set."""
    scored = [r for r in results if r["metrics"].get("mae") is not None]
    scored.sort(key=lambda r: r["metrics"]["mae"])
    return scored[0]