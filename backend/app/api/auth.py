"""Auth endpoints: local accounts, profile, and the demo sandbox."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..auth.security import get_current_user, hash_password, issue_token, limiter, verify_password
from ..config import get_settings, utc_now
from ..db import get_db
from ..models import Group, User
from ..schemas import LoginIn, ProfileUpdateIn, SignupIn
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
    db.commit()
    return _session(user)


@router.post("/auth/login")
def login(body: LoginIn, request: Request, db: Session = Depends(get_db)) -> dict:
    if not get_settings().allow_local_auth:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Use the main sign-in form.")
    limiter.check(request, "login", 10, 300)
    user = db.scalar(select(User).where(User.email == body.email.lower(), User.auth_provider == "local"))
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password.")
    return _session(user)


@router.get("/me")
def me(user: User = Depends(get_current_user)) -> dict:
    return user_out(user)


@router.patch("/me")
def update_me(body: ProfileUpdateIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    user.display_name = body.display_name.strip()
    from ..models import GroupMember  # keep member display names in sync

    for m in db.scalars(select(GroupMember).where(GroupMember.user_id == user.id)):
        m.display_name = user.display_name
    db.commit()
    return user_out(user)


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
