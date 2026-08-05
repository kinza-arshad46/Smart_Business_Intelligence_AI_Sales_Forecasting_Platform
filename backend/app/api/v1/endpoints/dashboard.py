"""
Lightweight aggregate endpoint used by the Streamlit dashboard landing page
to list datasets with a quick-glance KPI so the user doesn't have to open
each dataset individually.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.models.dataset import Dataset
from app.models.sales import SalesRecord
from app.models.user import User
from app.services import kpi_service
import pandas as pd

router = APIRouter(prefix="/overview", tags=["Business Intelligence"])


@router.get("")
def overview(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    q = db.query(Dataset)
    if current_user.role.value != "admin":
        q = q.filter(Dataset.owner_id == current_user.id)
    datasets = q.all()

    result = []
    for ds in datasets:
        rows = db.query(SalesRecord).filter(SalesRecord.dataset_id == ds.id).all()
        if rows:
            df = pd.DataFrame([{"order_date": r.order_date, "revenue": r.revenue, "quantity": r.quantity,
                                 "product": r.product, "category": r.category, "region": r.region} for r in rows])
            kpis = kpi_service.compute_kpis(df)
        else:
            kpis = {"total_revenue": 0, "total_orders": 0}
        result.append({
            "dataset_id": ds.id, "filename": ds.original_filename, "row_count": ds.row_count,
            "status": ds.status.value, "total_revenue": kpis.get("total_revenue", 0),
            "total_orders": kpis.get("total_orders", 0),
        })
    return result
