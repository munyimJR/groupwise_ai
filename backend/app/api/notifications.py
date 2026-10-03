"""Notifications for the signed-in user."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from ..auth.security import get_current_user
from ..db import get_db
from ..models import Group, Notification, User

router = APIRouter(tags=["notifications"])


@router.get("/notifications")
def list_notifications(user: User = Depends(get_current_user), db: Session = Depends(get_db),
                       limit: int = Query(40, ge=1, le=100)) -> dict:
    rows = db.execute(select(Notification, Group.name).outerjoin(Group, Group.id == Notification.group_id)
                      .where(Notification.user_id == user.id)
                      .order_by(Notification.created_at.desc()).limit(limit)).all()
    unread = db.scalar(select(func.count()).where(Notification.user_id == user.id, Notification.is_read.is_(False)))
    return {"unread": unread or 0,
            "items": [{"id": n.id, "kind": n.kind, "title": n.title, "body": n.body, "link": n.link, "is_read": n.is_read,
                       "group_id": n.group_id, "group_name": gname, "created_at": n.created_at.isoformat() + "Z"}
                      for n, gname in rows]}


@router.post("/notifications/read-all")
def read_all(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    db.execute(update(Notification).where(Notification.user_id == user.id).values(is_read=True))
    db.commit()
    return {"ok": True}


@router.post("/notifications/{notification_id}/read")
def read_one(notification_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    n = db.get(Notification, notification_id)
    if n is None or n.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Notification not found.")
    n.is_read = True
    db.commit()
    return {"ok": True}
