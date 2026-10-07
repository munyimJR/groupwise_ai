"""Controlled pilot experiment: group-level randomization and privacy-light activity logging.

Experiment "smart_nudges_v1" asks whether the AI intelligence layer changes behavior:

* control   — the exact ledger, settle-up (including the wallet) and goals, but no AI insights,
              recommendations, forecasts or nudges;
* treatment — the full GroupWise product.

Randomization is per group (members influence each other, so users can't be split), 50/50 by a hash of
the group id, assigned once and stored. Demo sandboxes and groups created before the pilot are never
assigned and always see the full product. Disabled unless EXPERIMENT_ENABLED=true.
"""
from __future__ import annotations

import hashlib
import threading

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import get_settings, local_now
from ..models import ActivityDay, ExperimentAssignment, Group, User

ARMS = ("control", "treatment")
_seen: set[tuple[str, str, str]] = set()
_lock = threading.Lock()


def assign_arm(db: Session, group: Group, creator: User) -> str | None:
    """Called when a real user creates a group while the experiment is running."""
    s = get_settings()
    if not s.experiment_enabled or creator.is_demo or creator.auth_provider not in ("local", "supabase"):
        return None
    digest = hashlib.sha256(f"{s.experiment_name}:{group.id}".encode()).digest()
    arm = ARMS[digest[0] % 2]
    db.add(ExperimentAssignment(group_id=group.id, experiment=s.experiment_name, arm=arm))
    return arm


def arm_of(db: Session, group_id: str) -> str:
    """'control' or 'treatment' (everything that isn't in the experiment gets the full product)."""
    if not get_settings().experiment_enabled:
        return "treatment"
    row = db.get(ExperimentAssignment, group_id)
    return row.arm if row else "treatment"


def touch_activity(db: Session, user: User, group_id: str) -> None:
    """Record that a real user used a group today (once per day; demo users are skipped)."""
    if user.is_demo or user.auth_provider not in ("local", "supabase"):
        return
    key = (user.id, group_id, local_now().date().isoformat())
    with _lock:
        if key in _seen:
            return
        _seen.add(key)
        if len(_seen) > 50_000:
            _seen.clear()
    day = local_now().date()
    if db.scalar(select(ActivityDay.id).where(ActivityDay.user_id == user.id, ActivityDay.group_id == group_id,
                                              ActivityDay.day == day)):
        return
    try:
        with db.begin_nested():
            db.add(ActivityDay(user_id=user.id, group_id=group_id, day=day))
        db.commit()
    except IntegrityError:
        db.rollback()
