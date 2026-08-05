import enum
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, Integer, ForeignKey, Enum, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.base import Base
class DatasetStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    VALIDATING = "validating"
    VALID = "valid"
    INVALID = "invalid"
    PROCESSED = "processed"


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[DatasetStatus] = mapped_column(Enum(DatasetStatus), default=DatasetStatus.UPLOADED)
    validation_report: Mapped[str] = mapped_column(Text, nullable=True)  # JSON string
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    owner = relationship("User", back_populates="datasets")
    sales_records = relationship("SalesRecord", back_populates="dataset", cascade="all, delete-orphan")
    models = relationship("MLModel", back_populates="dataset", cascade="all, delete-orphan")
