"""
Model evaluation utilities: standard regression metrics used to compare
forecasting algorithms and to compute the "forecast accuracy" KPI.
"""
import numpy as np


def evaluate(y_true, y_pred) -> dict:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    mae = float(np.mean(np.abs(y_true - y_pred)))
    rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))

    # MAPE, guarding against division by zero
    nonzero_mask = y_true != 0
    if nonzero_mask.sum() > 0:
        mape = float(np.mean(np.abs((y_true[nonzero_mask] - y_pred[nonzero_mask]) / y_true[nonzero_mask])) * 100)
    else:
        mape = None

    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    r2 = float(1 - ss_res / ss_tot) if ss_tot > 0 else None

    return {"mae": mae, "rmse": rmse, "mape": mape, "r2": r2}


def confidence_score_from_mape(mape: float) -> float:
    """Rough heuristic turning MAPE into a 0-1 'confidence' score for the UI."""
    if mape is None:
        return 0.5
    score = max(0.0, 1 - (mape / 100))
    return round(min(score, 0.99), 3)
