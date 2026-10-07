"""Groups, members and invite links."""
from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..analytics.ledger import balances
from ..auth.security import get_current_user
from ..config import get_settings, utc_now
from ..db import get_db
from ..models import Group, GroupMember, User, new_invite_code
from ..schemas import GroupCreateIn, GroupUpdateIn, JoinIn, MemberAddIn
from ..services.experiments import arm_of, assign_arm
from ..services.notifications import notify_members
from ..services.snapshot import load_snapshot
from ..synthetic.generator import COLORS
from .common import GroupAccess, group_access, member_out

router = APIRouter(tags=["groups"])


def _group_summary(db: Session, group: Group, me: GroupMember) -> dict:
    snap = load_snapshot(db, group)
    bal = balances(snap)
    mine = next((m for m in bal["members"] if m["member_id"] == me.id), None)
    since = snap.as_of - timedelta(days=30)
    last = max((e.occurred_at for e in snap.expenses), default=None)
    return {
        "id": group.id, "name": group.name, "description": group.description, "group_type": group.group_type,
        "member_count": len(snap.active_members), "my_member_id": me.id, "my_role": me.role,
        "my_net": mine["net"] if mine else 0,
        "total_30d": sum(e.amount for e in snap.expenses if e.occurred_at >= since),
        "total_all_time": bal["total_spent"], "expense_count": len(snap.expenses),
        "flagged_count": sum(1 for e in snap.expenses if e.anomaly_status == "flagged"),
        "last_activity": last.isoformat() if last else None,
        "members": [{"id": m.id, "name": m.name, "color": m.color} for m in snap.active_members[:6]],
        "experiment_arm": arm_of(db, group.id),
    }


@router.get("/groups")
def list_groups(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[dict]:
    rows = db.execute(select(Group, GroupMember).join(GroupMember, GroupMember.group_id == Group.id)
                      .where(GroupMember.user_id == user.id, GroupMember.status == "active")
                      .order_by(Group.created_at)).all()
    return [_group_summary(db, g, m) for g, m in rows]


@router.post("/groups", status_code=201)
def create_group(body: GroupCreateIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    group = Group(name=body.name.strip(), description=body.description, group_type=body.group_type, created_by=user.id)
    db.add(group)
    db.flush()
    owner = GroupMember(group_id=group.id, user_id=user.id, display_name=user.display_name, role="owner",
                        avatar_color=COLORS[0])
    db.add(owner)
    for i, name in enumerate(body.member_names):
        db.add(GroupMember(group_id=group.id, display_name=name, role="guest", avatar_color=COLORS[(i + 1) % len(COLORS)]))
    assign_arm(db, group, user)  # only while a controlled pilot experiment is running
    db.commit()
    return _group_summary(db, group, owner)


@router.get("/groups/{group_id}")
def get_group(access: GroupAccess = Depends(group_access), db: Session = Depends(get_db)) -> dict:
    g = access.group
    members = db.scalars(select(GroupMember).where(GroupMember.group_id == g.id).order_by(GroupMember.joined_at)).all()
    return {
        **_group_summary(db, g, access.member),
        "currency": g.currency, "monthly_budget": g.monthly_budget_paisa, "created_at": g.created_at.isoformat() + "Z",
        "data_version": g.data_version,
        "members_detail": [member_out(m, access.member.id) for m in members],
        "invite_code": g.invite_code,
        "invite_url": f"{get_settings().public_app_url.rstrip('/')}/join/{g.invite_code}",
    }


@router.patch("/groups/{group_id}")
def update_group(body: GroupUpdateIn, access: GroupAccess = Depends(group_access), db: Session = Depends(get_db)) -> dict:
    g = access.group
    if body.name is not None:
        g.name = body.name.strip()
    if body.description is not None:
        g.description = body.description
    if body.group_type is not None:
        g.group_type = body.group_type
    if body.monthly_budget is not None:
        g.monthly_budget_paisa = int(round(body.monthly_budget * 100)) or None
    g.data_version = Group.data_version + 1  # atomic in SQL: no lost updates
    db.commit()
    return get_group(access, db)


@router.post("/groups/{group_id}/members", status_code=201)
def add_member(body: MemberAddIn, access: GroupAccess = Depends(group_access), db: Session = Depends(get_db)) -> dict:
    count = db.query(GroupMember).filter(GroupMember.group_id == access.group.id).count()
    if count >= 50:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="A group can have at most 50 members.")
    m = GroupMember(group_id=access.group.id, display_name=body.display_name.strip(), role="guest",
                    avatar_color=COLORS[count % len(COLORS)])
    db.add(m)
    access.group.data_version = Group.data_version + 1  # atomic in SQL: no lost updates
    db.commit()
    return member_out(m, access.member.id)


@router.post("/groups/{group_id}/leave")
def leave_group(access: GroupAccess = Depends(group_access), db: Session = Depends(get_db)) -> dict:
    snap = load_snapshot(db, access.group)
    mine = next((m for m in balances(snap)["members"] if m["member_id"] == access.member.id), None)
    if mine and mine["net"] != 0:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            detail=f"Settle your balance (৳{abs(mine['net']) / 100:,.2f}) before leaving the group.")
    access.member.status = "left"
    access.member.left_at = utc_now()
    if access.member.role == "owner":
        successor = db.scalar(select(GroupMember).where(GroupMember.group_id == access.group.id, GroupMember.status == "active",
                                                        GroupMember.user_id.is_not(None), GroupMember.id != access.member.id))
        if successor:
            successor.role = "owner"
    access.group.data_version = Group.data_version + 1  # atomic in SQL: no lost updates
    db.commit()
    return {"ok": True}


@router.post("/groups/{group_id}/invite/regenerate")
def regenerate_invite(access: GroupAccess = Depends(group_access), db: Session = Depends(get_db)) -> dict:
    if access.member.role != "owner":
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Only the group owner can reset the invite link.")
    access.group.invite_code = new_invite_code()
    db.commit()
    return {"invite_code": access.group.invite_code,
            "invite_url": f"{get_settings().public_app_url.rstrip('/')}/join/{access.group.invite_code}"}


@router.get("/invites/{code}")
def invite_preview(code: str, db: Session = Depends(get_db)) -> dict:
    g = db.scalar(select(Group).where(Group.invite_code == code))
    if g is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="This invite link is invalid or has been reset.")
    members = db.scalars(select(GroupMember).where(GroupMember.group_id == g.id, GroupMember.status == "active")).all()
    return {"group_name": g.name, "group_type": g.group_type, "member_count": len(members),
            "claimable_members": [{"id": m.id, "display_name": m.display_name} for m in members if m.user_id is None]}


@router.post("/invites/{code}/join")
def join_group(code: str, body: JoinIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    g = db.scalar(select(Group).where(Group.invite_code == code))
    if g is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="This invite link is invalid or has been reset.")
    existing = db.scalar(select(GroupMember).where(GroupMember.group_id == g.id, GroupMember.user_id == user.id))
    if existing:
        existing.status, existing.left_at = "active", None
        member = existing
    elif body.claim_member_id:
        member = db.scalar(select(GroupMember).where(GroupMember.id == body.claim_member_id, GroupMember.group_id == g.id,
                                                     GroupMember.user_id.is_(None), GroupMember.status == "active"))
        if member is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="That member can't be claimed.")
        member.user_id, member.role = user.id, "member"
    else:
        count = db.query(GroupMember).filter(GroupMember.group_id == g.id).count()
        member = GroupMember(group_id=g.id, user_id=user.id, display_name=user.display_name, role="member",
                             avatar_color=COLORS[count % len(COLORS)])
        db.add(member)
    g.data_version = Group.data_version + 1  # atomic in SQL: no lost updates
    db.flush()
    notify_members(db, g, exclude_user_id=user.id, kind="member", title=f"New member in {g.name}",
                   body=f"{member.display_name} joined the group.", link=f"/g/{g.id}/members")
    db.commit()
    return {"group_id": g.id, "member_id": member.id}
