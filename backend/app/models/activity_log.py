from datetime import datetime

from sqlalchemy import Integer, String, ForeignKey, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ActivityLog(Base):
    """Audit trail: who did what and when (login, upload, train, predict, etc.)."""
    __tablename__ = "activity_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    details: Mapped[str] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="activity_logs")
