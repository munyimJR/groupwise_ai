"""In-app notifications (deduplicated per user)."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Group, GroupMember, Notification, User


def notify_user(db: Session, user_id: str, group_id: str | None, kind: str, title: str, body: str,
                link: str | None = None, dedupe_key: str | None = None) -> None:
    if dedupe_key and db.scalar(select(Notification.id).where(Notification.user_id == user_id,
                                                              Notification.dedupe_key == dedupe_key)):
        return
    db.add(Notification(user_id=user_id, group_id=group_id, kind=kind, title=title[:120], body=body[:400],
                        link=link, dedupe_key=dedupe_key))


def notify_members(db: Session, group: Group, exclude_user_id: str | None, kind: str, title: str, body: str,
                   link: str | None = None, dedupe_key: str | None = None) -> None:
    rows = db.execute(
        select(GroupMember.user_id).join(User, User.id == GroupMember.user_id)
        .where(GroupMember.group_id == group.id, GroupMember.status == "active", GroupMember.user_id.is_not(None))
    ).scalars().all()
    for uid in rows:
        if uid != exclude_user_id:
            notify_user(db, uid, group.id, kind, title, body, link, dedupe_key)
