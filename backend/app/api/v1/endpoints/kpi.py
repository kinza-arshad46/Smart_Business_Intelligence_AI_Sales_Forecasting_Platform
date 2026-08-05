from typing import Optional

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.models.dataset import Dataset
from app.models.ml_model import MLModel
from app.models.sales import SalesRecord
from app.models.user import User
from app.schemas.kpi import DashboardData, KPISummary, TrendPoint, BreakdownItem
from app.services import kpi_service

router = APIRouter(prefix="/kpi", tags=["Business Intelligence"])


def _load_df(db: Session, dataset_id: int) -> pd.DataFrame:
    rows = db.query(SalesRecord).filter(SalesRecord.dataset_id == dataset_id).all()
    if not rows:
        return pd.DataFrame(columns=["order_date", "product", "category", "region", "quantity", "unit_price", "revenue"])
    return pd.DataFrame([{
        "order_date": r.order_date, "product": r.product, "category": r.category,
        "region": r.region, "quantity": r.quantity, "unit_price": r.unit_price, "revenue": r.revenue,
    } for r in rows])


@router.get("/{dataset_id}/summary", response_model=KPISummary)
def kpi_summary(dataset_id: int, sales_target: Optional[float] = Query(None),
                 db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    df = _load_df(db, dataset_id)
    active_model = (
        db.query(MLModel)
        .filter(MLModel.dataset_id == dataset_id, MLModel.is_active == True)  # noqa: E712
        .order_by(MLModel.trained_at.desc())
        .first()
    )
    mape = active_model.mape if active_model else None
    kpis = kpi_service.compute_kpis(df, active_model_mape=mape, sales_target=sales_target)
    return KPISummary(**kpis)


@router.get("/{dataset_id}/dashboard", response_model=DashboardData)
def dashboard_data(dataset_id: int, freq: str = Query("D", pattern="^(D|W|ME)$"),
                    sales_target: Optional[float] = Query(None),
                    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    df = _load_df(db, dataset_id)
    active_model = (
        db.query(MLModel)
        .filter(MLModel.dataset_id == dataset_id, MLModel.is_active == True)  # noqa: E712
        .order_by(MLModel.trained_at.desc())
        .first()
    )
    mape = active_model.mape if active_model else None

    kpis = kpi_service.compute_kpis(df, active_model_mape=mape, sales_target=sales_target)
    trend = kpi_service.revenue_trend(df, freq=freq)
    by_category = kpi_service.breakdown_by(df, "category")
    by_region = kpi_service.breakdown_by(df, "region")
    by_product = kpi_service.breakdown_by(df, "product")[:10]  # top 10 products only

    return DashboardData(
        kpis=KPISummary(**kpis),
        revenue_trend=[TrendPoint(**t) for t in trend],
        by_category=[BreakdownItem(**c) for c in by_category],
        by_region=[BreakdownItem(**r) for r in by_region],
        by_product=[BreakdownItem(**p) for p in by_product],
    )
