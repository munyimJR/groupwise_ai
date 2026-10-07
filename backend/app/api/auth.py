"""Auth endpoints: local accounts, profile, and the demo sandbox."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import delete, or_, select, update
from sqlalchemy.orm import Session

from ..auth.security import (
    _bearer,
    get_current_user,
    hash_password,
    issue_token,
    limiter,
    revoke_all_sessions,
    revoke_token,
    token_claims,
    verify_password,
)
from ..config import get_settings, utc_now
from ..db import get_db
from ..models import Expense, Goal, GoalContribution, Group, GroupMember, Settlement, User
from ..schemas import DeleteAccountIn, LoginIn, ProfileUpdateIn, SignupIn
from ..services.audit import audit, recent_failures
from ..synthetic.seed import create_demo_user, seed_workspace
from .common import user_out

router = APIRouter(tags=["auth"])
log = logging.getLogger("groupwise.auth")


def _session(user: User) -> dict:
    token, expires = issue_token(user)
    return {"access_token": token, "token_type": "bearer", "expires_at": expires.isoformat(), "user": user_out(user)}


@router.post("/auth/signup")
def signup(body: SignupIn, request: Request, db: Session = Depends(get_db)) -> dict:
    if not get_settings().allow_local_auth:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Use the main sign-up form.")
    limiter.check(request, "signup", 10, 3600)
    email = body.email.lower()
    if db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, detail="An account with this email already exists.")
    user = User(email=email, display_name=body.display_name.strip(), password_hash=hash_password(body.password),
                auth_provider="local")
    db.add(user)
    db.flush()
    audit(db, "signup", request=request, user_id=user.id)
    db.commit()
    return _session(user)


@router.post("/auth/login")
def login(body: LoginIn, request: Request, db: Session = Depends(get_db)) -> dict:
    if not get_settings().allow_local_auth:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Use the main sign-in form.")
    limiter.check(request, "login", 10, 300)
    settings = get_settings()
    email = body.email.lower()
    # Per-account lockout: the per-IP limit alone doesn't stop slow guessing spread over many addresses.
    if recent_failures(db, "login", email, settings.login_lockout_minutes) >= settings.login_max_failures:
        audit(db, "login", request=request, outcome="denied", subject=email, commit=True, reason="locked")
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                            detail=f"Too many failed attempts. Try again in {settings.login_lockout_minutes} minutes.")
    user = db.scalar(select(User).where(User.email == email, User.auth_provider == "local"))
    if user is None or not verify_password(body.password, user.password_hash):
        audit(db, "login", request=request, outcome="failed", subject=email, commit=True)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password.")
    audit(db, "login", request=request, user_id=user.id, commit=True)
    return _session(user)


@router.post("/auth/logout")
def logout(request: Request, creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
           user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    """Revoke this session's token on the server, so it stops working now rather than at expiry."""
    revoke_token(db, token_claims(creds.credentials))
    audit(db, "logout", request=request, user_id=user.id)
    db.commit()
    return {"ok": True}


@router.post("/auth/logout-all")
def logout_all(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    """Sign out on every device: every token issued before now is rejected."""
    revoke_all_sessions(db, user.id)
    audit(db, "logout_all", request=request, user_id=user.id)
    db.commit()
    return {"ok": True}


@router.get("/me")
def me(user: User = Depends(get_current_user)) -> dict:
    return user_out(user)


@router.patch("/me")
def update_me(body: ProfileUpdateIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    user.display_name = body.display_name.strip()
    for m in db.scalars(select(GroupMember).where(GroupMember.user_id == user.id)):
        m.display_name = user.display_name
    db.commit()
    return user_out(user)


def _iso(dt) -> str | None:
    return dt.isoformat() if dt else None


@router.get("/me/export")
def export_my_data(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    """Everything GroupWise stores that is linked to you, as JSON (data portability)."""
    memberships = db.scalars(select(GroupMember).where(GroupMember.user_id == user.id)).all()
    member_ids = [m.id for m in memberships]
    names = dict(db.execute(select(Group.id, Group.name).where(Group.id.in_([m.group_id for m in memberships]))).all())
    expenses = db.scalars(select(Expense).where(or_(Expense.payer_member_id.in_(member_ids),
                                                    Expense.created_by_user_id == user.id))).all()
    settlements = db.scalars(select(Settlement).where(or_(Settlement.from_member_id.in_(member_ids),
                                                          Settlement.to_member_id.in_(member_ids)))).all()
    contributions = db.scalars(select(GoalContribution).where(GoalContribution.member_id.in_(member_ids))).all()
    audit(db, "data_export", request=request, user_id=user.id, commit=True)
    return {
        "exported_at": _iso(utc_now()),
        "profile": {"id": user.id, "email": user.email, "display_name": user.display_name,
                    "auth_provider": user.auth_provider, "created_at": _iso(user.created_at)},
        "groups": [{"group_id": m.group_id, "group_name": names.get(m.group_id), "role": m.role, "status": m.status,
                    "joined_at": _iso(m.joined_at)} for m in memberships],
        "expenses": [{"id": e.id, "group_id": e.group_id, "description": e.description, "amount_paisa": e.amount_paisa,
                      "category": e.category, "occurred_at": _iso(e.occurred_at), "deleted": e.is_deleted,
                      "you_paid": e.payer_member_id in member_ids} for e in expenses],
        "settlements": [{"id": x.id, "group_id": x.group_id, "amount_paisa": x.amount_paisa,
                         "direction": "sent" if x.from_member_id in member_ids else "received",
                         "occurred_at": _iso(x.occurred_at)} for x in settlements],
        "goal_contributions": [{"id": c.id, "goal_id": c.goal_id, "amount_paisa": c.amount_paisa,
                                "occurred_at": _iso(c.occurred_at)} for c in contributions],
    }


@router.delete("/me")
def delete_my_account(body: DeleteAccountIn, request: Request, user: User = Depends(get_current_user),
                      db: Session = Depends(get_db)) -> dict:
    """Delete the account. Ledgers stay correct for everyone else: past expenses and settlements remain,
    but the membership becomes an anonymous "Former member" with no link back to the person."""
    if user.is_demo:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Demo sessions delete themselves automatically.")
    if body.confirm != "DELETE":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Type DELETE to confirm.")
    uid = user.id
    db.execute(update(GroupMember).where(GroupMember.user_id == uid)
               .values(user_id=None, display_name="Former member", status="left", left_at=utc_now()))
    db.execute(update(Expense).where(Expense.created_by_user_id == uid).values(created_by_user_id=None))
    db.execute(update(Settlement).where(Settlement.created_by_user_id == uid).values(created_by_user_id=None))
    db.execute(update(Goal).where(Goal.created_by_user_id == uid).values(created_by_user_id=None))
    db.execute(update(Group).where(Group.created_by == uid).values(created_by=None))
    db.delete(user)  # notifications, activity and session rows cascade
    audit(db, "account_deleted", request=request, user_id=uid)
    db.commit()
    return {"ok": True}


def cleanup_expired_demos(db: Session) -> int:
    expired = db.scalars(select(User.id).where(User.is_demo.is_(True), User.expires_at < utc_now())).all()
    if expired:
        db.execute(delete(Group).where(Group.created_by.in_(expired)))
        db.execute(delete(User).where(User.id.in_(expired)))
        db.commit()
    return len(expired)


@router.post("/demo/session")
def demo_session(request: Request, db: Session = Depends(get_db)) -> dict:
    settings = get_settings()
    if not settings.demo_enabled:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="The demo sandbox is disabled.")
    limiter.check(request, "demo", 20, 3600)
    try:
        cleanup_expired_demos(db)
    except Exception:  # cleanup must never block a new demo
        db.rollback()
        log.exception("demo cleanup failed")
    user = create_demo_user(db, settings.demo_ttl_hours)
    groups = seed_workspace(db, user)
    db.commit()
    return {**_session(user), "groups": [{"id": g.id, "name": g.name} for g in groups]}


@router.post("/me/sample-data")
def load_sample_data(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    """Let a real account explore with the same synthetic groups as the demo."""
    groups = seed_workspace(db, user)
    db.commit()
    return {"groups": [{"id": g.id, "name": g.name} for g in groups]}
