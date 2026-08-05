import enum
from datetime import datetime, timezone

from sqlalchemy import String, Boolean, DateTime, Enum, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
# Old line:
# from app.db.base import Base

# New line:
from ..db.base import Base


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    USER = "user"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.USER, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    datasets = relationship("Dataset", back_populates="owner", cascade="all, delete-orphan")
    activity_logs = relationship("ActivityLog", back_populates="user", cascade="all, delete-orphan")
