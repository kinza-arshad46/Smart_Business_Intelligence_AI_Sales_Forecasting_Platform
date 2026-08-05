from datetime import datetime, date

from sqlalchemy import Integer, Float, ForeignKey, DateTime, Date, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    model_id: Mapped[int] = mapped_column(ForeignKey("ml_models.id"), nullable=False)
    target_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    predicted_revenue: Mapped[float] = mapped_column(Float, nullable=False)
    lower_bound: Mapped[float] = mapped_column(Float, nullable=True)
    upper_bound: Mapped[float] = mapped_column(Float, nullable=True)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=True)  # 0-1
    segment: Mapped[str] = mapped_column(String(120), nullable=True)  # e.g. category/region filter used
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    model = relationship("MLModel", back_populates="predictions")
