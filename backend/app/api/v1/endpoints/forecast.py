import json
from datetime import datetime
from typing import List

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.models.dataset import Dataset
from app.models.ml_model import MLModel, ModelStatus
from app.models.sales import SalesRecord
from app.models.prediction import Prediction
from app.models.user import User
from app.schemas.prediction import TrainRequest, ForecastRequest, ForecastResponse, ForecastPoint, ModelCompareOut
from app.services import forecasting
from app.services.activity_service import log_activity
from app.ml.trainer import AVAILABLE_ALGORITHMS

router = APIRouter(prefix="/forecast", tags=["Machine Learning"])


def _load_sales_df(db: Session, dataset_id: int, category: str = None, region: str = None) -> pd.DataFrame:
    q = db.query(SalesRecord).filter(SalesRecord.dataset_id == dataset_id)
    if category:
        q = q.filter(SalesRecord.category == category)
    if region:
        q = q.filter(SalesRecord.region == region)
    rows = q.all()
    if not rows:
        return pd.DataFrame(columns=["order_date", "product", "category", "region", "quantity", "unit_price", "revenue"])
    return pd.DataFrame([{
        "order_date": r.order_date, "product": r.product, "category": r.category,
        "region": r.region, "quantity": r.quantity, "unit_price": r.unit_price, "revenue": r.revenue,
    } for r in rows])


@router.get("/algorithms")
def list_algorithms():
    return {"available": AVAILABLE_ALGORITHMS,
            "note": "xgboost / lightgbm / prophet are used automatically if installed; "
                    "otherwise training falls back to gradient_boosting / random_forest "
                    "so the platform keeps working without errors."}


@router.post("/train", response_model=List[ModelCompareOut])
def train_models(payload: TrainRequest, request: Request, db: Session = Depends(get_db),
                  current_user: User = Depends(get_current_user)):
    dataset = db.query(Dataset).filter(Dataset.id == payload.dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if current_user.role.value != "admin" and dataset.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    sales_df = _load_sales_df(db, dataset.id)
    if sales_df.empty:
        raise HTTPException(status_code=400, detail="Dataset has no sales rows to train on.")

    try:
        results = forecasting.train_models_for_dataset(
            dataset_id=dataset.id, sales_df=sales_df,
            algorithms=payload.algorithms, test_size=payload.test_size,
            tune=payload.tune_hyperparameters,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Deactivate previous models for this dataset, then insert new ones
    db.query(MLModel).filter(MLModel.dataset_id == dataset.id).update({"is_active": False})

    saved_rows = []
    for r in results:
        model_row = MLModel(
            dataset_id=dataset.id,
            algorithm=r["algorithm"],
            version=r["version"],
            file_path=r["file_path"],
            status=ModelStatus.READY,
            mae=r["mae"], rmse=r["rmse"], mape=r["mape"], r2=r["r2"],
            hyperparameters=json.dumps(r["hyperparameters"], default=str),
            is_active=r["is_active"],
        )
        db.add(model_row)
        saved_rows.append(model_row)

    db.commit()
    for row in saved_rows:
        db.refresh(row)

    log_activity(db, current_user.id, "model_train",
                 {"dataset_id": dataset.id, "algorithms": payload.algorithms},
                 request.client.host if request.client else None)

    return [
        ModelCompareOut(
            id=m.id, algorithm=m.algorithm, version=m.version, mae=m.mae, rmse=m.rmse,
            mape=m.mape, r2=m.r2, is_active=m.is_active, status=m.status.value,
            trained_at=m.trained_at.isoformat(),
        ) for m in saved_rows
    ]


@router.get("/models/{dataset_id}", response_model=List[ModelCompareOut])
def compare_models(dataset_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    models = db.query(MLModel).filter(MLModel.dataset_id == dataset_id).order_by(MLModel.trained_at.desc()).all()
    return [
        ModelCompareOut(
            id=m.id, algorithm=m.algorithm, version=m.version, mae=m.mae, rmse=m.rmse,
            mape=m.mape, r2=m.r2, is_active=m.is_active, status=m.status.value,
            trained_at=m.trained_at.isoformat(),
        ) for m in models
    ]


@router.post("/predict", response_model=ForecastResponse)
def predict(payload: ForecastRequest, request: Request, db: Session = Depends(get_db),
            current_user: User = Depends(get_current_user)):
    q = db.query(MLModel).filter(MLModel.dataset_id == payload.dataset_id, MLModel.status == ModelStatus.READY)
    if payload.algorithm:
        model_row = q.filter(MLModel.algorithm == payload.algorithm).order_by(MLModel.trained_at.desc()).first()
    else:
        model_row = q.filter(MLModel.is_active == True).order_by(MLModel.trained_at.desc()).first()  # noqa: E712

    if not model_row:
        raise HTTPException(
            status_code=404,
            detail="No trained model found for this dataset. Call /forecast/train first.",
        )

    sales_df = _load_sales_df(db, payload.dataset_id, payload.category, payload.region)
    if sales_df.empty:
        raise HTTPException(status_code=400, detail="No sales data available for the requested filters.")

    try:
        fc_df = forecasting.generate_forecast(model_row, sales_df, payload.horizon_days)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Forecast generation failed: {e}")

    # Persist predictions for audit / dashboard reuse
    segment = f"category={payload.category or 'all'};region={payload.region or 'all'}"
    pred_rows = [
        Prediction(
            model_id=model_row.id,
            target_date=row["date"],
            predicted_revenue=float(row["predicted_revenue"]),
            lower_bound=float(row.get("lower_bound", row["predicted_revenue"])),
            upper_bound=float(row.get("upper_bound", row["predicted_revenue"])),
            confidence_score=float(row.get("confidence_score", 0.5)),
            segment=segment,
        )
        for _, row in fc_df.iterrows()
    ]
    db.bulk_save_objects(pred_rows)
    db.commit()

    log_activity(db, current_user.id, "forecast_predict",
                 {"dataset_id": payload.dataset_id, "horizon_days": payload.horizon_days},
                 request.client.host if request.client else None)

    points = [
        ForecastPoint(
            date=row["date"], predicted_revenue=round(float(row["predicted_revenue"]), 2),
            lower_bound=round(float(row.get("lower_bound", row["predicted_revenue"])), 2),
            upper_bound=round(float(row.get("upper_bound", row["predicted_revenue"])), 2),
            confidence_score=float(row.get("confidence_score", 0.5)),
        )
        for _, row in fc_df.iterrows()
    ]

    return ForecastResponse(
        model_id=model_row.id, algorithm=model_row.algorithm, horizon_days=payload.horizon_days,
        generated_at=datetime.utcnow().isoformat(),
        points=points,
        evaluation={"mae": model_row.mae, "rmse": model_row.rmse, "mape": model_row.mape, "r2": model_row.r2},
    )
