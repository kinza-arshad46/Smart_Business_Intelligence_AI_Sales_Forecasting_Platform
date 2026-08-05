from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_admin, get_current_user
from app.models.user import User
from app.models.activity_log import ActivityLog
from app.schemas.user import UserOut, UserUpdate

router = APIRouter(prefix="/users", tags=["User Management"])


@router.get("", response_model=List[UserOut])
def list_users(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    """Admin only: list all registered users."""
    return db.query(User).order_by(User.created_at.desc()).all()


@router.patch("/{user_id}", response_model=UserOut)
def update_user(user_id: int, payload: UserUpdate, db: Session = Depends(get_db),
                 admin: User = Depends(get_current_admin)):
    """Admin only: activate/deactivate a user or change their role."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.role is not None:
        user.role = payload.role

    db.commit()
    db.refresh(user)
    return user


@router.get("/me/activity")
def my_activity(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Any logged-in user: view their own activity log."""
    logs = (
        db.query(ActivityLog)
        .filter(ActivityLog.user_id == current_user.id)
        .order_by(ActivityLog.created_at.desc())
        .limit(200)
        .all()
    )
    return [
        {"action": l.action, "details": l.details, "created_at": l.created_at.isoformat()}
        for l in logs
    ]


@router.get("/activity/all")
def all_activity(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    """Admin only: view activity logs for every user."""
    logs = db.query(ActivityLog).order_by(ActivityLog.created_at.desc()).limit(500).all()
    return [
        {
            "user_id": l.user_id, "action": l.action, "details": l.details,
            "ip_address": l.ip_address, "created_at": l.created_at.isoformat(),
        }
        for l in logs
    ]
