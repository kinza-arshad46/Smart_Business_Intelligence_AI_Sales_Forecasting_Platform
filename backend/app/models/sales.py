from datetime import datetime, date

from sqlalchemy import String, Integer, Float, Date, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.base import Base


class SalesRecord(Base):
    """
    Normalized sales record parsed from an uploaded CSV/Excel file.
    Column mapping is flexible (see services/data_processing.py) so it can
    absorb differently named source columns.
    """
    __tablename__ = "sales_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id"), nullable=False, index=True)

    order_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    product: Mapped[str] = mapped_column(String(255), nullable=True, index=True)
    category: Mapped[str] = mapped_column(String(120), nullable=True, index=True)
    region: Mapped[str] = mapped_column(String(120), nullable=True, index=True)
    quantity: Mapped[float] = mapped_column(Float, default=0)
    unit_price: Mapped[float] = mapped_column(Float, default=0)
    revenue: Mapped[float] = mapped_column(Float, default=0)
    cost: Mapped[float] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    dataset = relationship("Dataset", back_populates="sales_records")
