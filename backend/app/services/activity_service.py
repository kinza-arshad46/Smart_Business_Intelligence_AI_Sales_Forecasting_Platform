"""Writes user activity/audit log entries."""
import json
from sqlalchemy.orm import Session

from app.models.activity_log import ActivityLog


def log_activity(db: Session, user_id: int, action: str, details: dict | None = None,
                  ip_address: str | None = None) -> None:
    entry = ActivityLog(
        user_id=user_id,
        action=action,
        details=json.dumps(details or {}),
        ip_address=ip_address,
    )
    db.add(entry)
    db.commit()
