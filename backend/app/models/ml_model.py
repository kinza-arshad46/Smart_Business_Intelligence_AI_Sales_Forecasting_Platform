import enum
from datetime import datetime

from sqlalchemy import String, Integer, Float, ForeignKey, DateTime, Enum, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.base import Base


class ModelStatus(str, enum.Enum):
    TRAINING = "training"
    READY = "ready"
    FAILED = "failed"
    ARCHIVED = "archived"


class MLModel(Base):
    """Registry entry for a single trained forecasting model."""
    __tablename__ = "ml_models"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id"), nullable=False)
    algorithm: Mapped[str] = mapped_column(String(50), nullable=False)  # xgboost | lightgbm | prophet | random_forest | gradient_boosting
    version: Mapped[str] = mapped_column(String(20), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=True)
    status: Mapped[ModelStatus] = mapped_column(Enum(ModelStatus), default=ModelStatus.TRAINING)

    mae: Mapped[float] = mapped_column(Float, nullable=True)
    rmse: Mapped[float] = mapped_column(Float, nullable=True)
    mape: Mapped[float] = mapped_column(Float, nullable=True)
    r2: Mapped[float] = mapped_column(Float, nullable=True)

    hyperparameters: Mapped[str] = mapped_column(Text, nullable=True)  # JSON string
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)  # currently used for /predict

    trained_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    dataset = relationship("Dataset", back_populates="models")
    predictions = relationship("Prediction", back_populates="model", cascade="all, delete-orphan")
