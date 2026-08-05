from datetime import date
from typing import Optional, List

from pydantic import BaseModel, Field


class ForecastRequest(BaseModel):
    dataset_id: int
    horizon_days: int = Field(30, ge=1, le=365, description="How many days ahead to forecast")
    category: Optional[str] = None
    region: Optional[str] = None
    algorithm: Optional[str] = Field(
        None, description="xgboost | lightgbm | prophet | random_forest | gradient_boosting. "
                           "If omitted, the best available trained model is used."
    )


class ForecastPoint(BaseModel):
    date: date
    predicted_revenue: float
    lower_bound: float
    upper_bound: float
    confidence_score: float


class ForecastResponse(BaseModel):
    model_id: int
    algorithm: str
    horizon_days: int
    generated_at: str
    points: List[ForecastPoint]
    evaluation: dict


class TrainRequest(BaseModel):
    dataset_id: int
    algorithms: List[str] = Field(
        default_factory=lambda: ["gradient_boosting", "random_forest", "xgboost", "lightgbm", "prophet"],
        description="Algorithms to train and compare. Unavailable libraries are skipped automatically.",
    )
    tune_hyperparameters: bool = False
    test_size: float = Field(0.2, gt=0.0, lt=0.5)


class ModelCompareOut(BaseModel):
    id: int
    algorithm: str
    version: str
    mae: Optional[float]
    rmse: Optional[float]
    mape: Optional[float]
    r2: Optional[float]
    is_active: bool
    status: str
    trained_at: str

    class Config:
        from_attributes = True
