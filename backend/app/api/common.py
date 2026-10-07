"""Shared API helpers: group access control and serializers."""
from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth.security import get_current_user
from ..db import get_db
from ..ml.taxonomy import get_subcategory
from ..models import Expense, Group, GroupMember, User
from ..services.audit import probes
from ..services.experiments import touch_activity


def user_out(user: User) -> dict:
    return {"id": user.id, "email": user.email, "display_name": user.display_name, "auth_provider": user.auth_provider,
            "is_demo": user.is_demo, "avatar_color": user.avatar_color,
            "expires_at": user.expires_at.isoformat() + "Z" if user.expires_at else None}


class GroupAccess:
    def __init__(self, group: Group, member: GroupMember, user: User):
        self.group, self.member, self.user = group, member, user


def group_access(group_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db),
                 request: Request = None) -> GroupAccess:
    """The caller must be an active member. Non-members get 404 so group ids can't be probed, and a caller
    who keeps hitting groups they don't belong to is blocked for a while (see ProbeDetector)."""
    probes.check(user.id)
    group = db.get(Group, group_id)
    member = db.scalar(select(GroupMember).where(GroupMember.group_id == group_id, GroupMember.user_id == user.id,
                                                 GroupMember.status == "active")) if group else None
    if group is None or member is None:
        probes.miss(db, request, user.id, group_id)
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Group not found.")
    touch_activity(db, user, group_id)  # retention metric for the pilot (real accounts only)
    return GroupAccess(group, member, user)


def member_out(m: GroupMember, me_id: str | None = None) -> dict:
    return {"id": m.id, "display_name": m.display_name, "role": m.role, "status": m.status, "avatar_color": m.avatar_color,
            "is_app_user": m.user_id is not None, "is_you": m.id == me_id, "joined_at": m.joined_at.isoformat()}


def expense_out(e: Expense, names: dict[str, str], detail: bool = False) -> dict:
    sub = get_subcategory(e.subcategory)
    out = {
        "id": e.id, "description": e.description, "merchant": e.merchant, "amount": e.amount_paisa,
        "payer_member_id": e.payer_member_id, "payer_name": names.get(e.payer_member_id, "Former member"),
        "category": e.category, "subcategory": e.subcategory, "subcategory_label": sub.label,
        "expense_type": e.expense_type, "category_source": e.category_source,
        "category_confidence": e.category_confidence, "occurred_at": e.occurred_at.isoformat(),
        "payment_method": e.payment_method, "split_method": e.split_method,
        "anomaly": {"score": e.anomaly_score, "status": e.anomaly_status,
                    "reasons": (e.anomaly_reasons or []) if detail else (e.anomaly_reasons or [])[:1]},
        "participant_count": len(e.splits),
    }
    if detail:
        out["notes"] = e.notes
        out["created_at"] = e.created_at.isoformat() + "Z"
        out["participants"] = [{"member_id": s.member_id, "name": names.get(s.member_id, "Former member"),
                                "share": s.share_paisa} for s in e.splits]
    return out


def member_names(db: Session, group_id: str) -> dict[str, str]:
    return dict(db.execute(select(GroupMember.id, GroupMember.display_name).where(GroupMember.group_id == group_id)).all())
