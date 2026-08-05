from datetime import datetime
from typing import Optional, List, Dict, Any

from pydantic import BaseModel

from app.models.dataset import DatasetStatus


class DatasetOut(BaseModel):
    id: int
    filename: str
    original_filename: str
    row_count: int
    status: DatasetStatus
    uploaded_at: datetime

    class Config:
        from_attributes = True


class DatasetValidationReport(BaseModel):
    is_valid: bool
    total_rows: int
    valid_rows: int
    invalid_rows: int
    missing_columns: List[str] = []
    detected_columns: Dict[str, str] = {}
    warnings: List[str] = []
    errors: List[str] = []


class SalesRecordOut(BaseModel):
    order_date: str
    product: Optional[str]
    category: Optional[str]
    region: Optional[str]
    quantity: float
    unit_price: float
    revenue: float

    class Config:
        from_attributes = True
