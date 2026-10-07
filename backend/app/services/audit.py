"""Audit log for security-relevant events. Hashes identifiers instead of storing emails or raw IPs."""
from __future__ import annotations

import hashlib
import logging
import threading
import time
from collections import defaultdict, deque
from datetime import timedelta

from fastapi import HTTPException, Request, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from ..config import get_settings, utc_now
from ..models import AuditLog

log = logging.getLogger("groupwise.audit")


def _h(value: str | None) -> str | None:
    if not value:
        return None
    return hashlib.sha256(f"{get_settings().jwt_secret}:{value.lower()}".encode()).hexdigest()[:16]


def client_ip(request: Request | None) -> str:
    if request is None:
        return "?"
    if get_settings().trust_proxy:
        forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        if forwarded:
            return forwarded
    return request.client.host if request.client else "?"


def audit(db: Session, action: str, *, request: Request | None = None, user_id: str | None = None,
          group_id: str | None = None, outcome: str = "ok", subject: str | None = None, commit: bool = False,
          **detail) -> None:
    """Record an event. `commit=True` for events that must survive the request failing (e.g. a denied login)."""
    db.add(AuditLog(action=action, outcome=outcome, user_id=user_id, group_id=group_id, ip_hash=_h(client_ip(request)),
                    subject_hash=_h(subject), detail=detail or None))
    if commit:
        db.commit()
    log.info("audit %s %s user=%s group=%s", action, outcome, user_id, group_id)


def recent_failures(db: Session, action: str, subject: str, minutes: int) -> int:
    since = utc_now() - timedelta(minutes=minutes)
    return db.scalar(select(func.count()).select_from(AuditLog).where(
        AuditLog.action == action, AuditLog.outcome == "failed", AuditLog.subject_hash == _h(subject),
        AuditLog.created_at >= since)) or 0


# ----------------------------------------------------------------------------- abuse detection
class ProbeDetector:
    """Flags callers who keep asking for groups they don't belong to (id enumeration / IDOR probing).

    Group routes answer non-members with 404; a few are normal (stale links), dozens in minutes are not.
    Past the threshold the caller is blocked for the rest of the window and an `abuse_suspected` event is audited.
    """

    def __init__(self, threshold: int = 20, window_seconds: int = 600) -> None:
        self.threshold, self.window = threshold, window_seconds
        self._misses: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def _count(self, key: str, add: bool) -> int:
        now = time.monotonic()
        with self._lock:
            q = self._misses[key]
            while q and now - q[0] > self.window:
                q.popleft()
            if add:
                q.append(now)
            return len(q)

    def check(self, user_id: str) -> None:
        if get_settings().rate_limit_enabled and self._count(user_id, add=False) >= self.threshold:
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                                detail="Too many requests for groups you are not part of. Please wait a while.")

    def miss(self, db: Session, request: Request | None, user_id: str, group_id: str) -> None:
        if self._count(user_id, add=True) == self.threshold:
            audit(db, "abuse_suspected", request=request, user_id=user_id, group_id=group_id, outcome="denied",
                  commit=True, reason="group_probing")

    def reset(self) -> None:
        with self._lock:
            self._misses.clear()


probes = ProbeDetector()


# ----------------------------------------------------------------------------- request audit trail
# Mutating routes recorded automatically. Auth routes write their own, richer events.
_SKIP = ("/api/auth/", "/api/demo/", "/api/categorize", "/api/notifications", "/api/integrations/")
_SKIP_SUFFIX = ("/what-if", "/copilot", "/statement/preview")


def _write_request_event(action: str, outcome: str, user_id: str | None, group_id: str | None, ip: str,
                         status_code: int) -> None:
    from ..db import SessionLocal

    try:
        with SessionLocal() as db:
            db.add(AuditLog(action=action, outcome=outcome, user_id=user_id, group_id=group_id, ip_hash=_h(ip),
                            detail={"status": status_code}))
            db.commit()
    except Exception:  # the audit trail must never break the request it describes
        log.exception("audit write failed for %s", action)


class AuditMiddleware:
    """Pure ASGI middleware: one audit row per state-changing API request (who, which group, what, outcome)."""

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] not in ("POST", "PUT", "PATCH", "DELETE"):
            return await self.app(scope, receive, send)
        path = scope["path"]
        if not path.startswith("/api/") or path.startswith(_SKIP) or path.endswith(_SKIP_SUFFIX):
            return await self.app(scope, receive, send)
        status_box = [500]

        async def capture(message):
            if message["type"] == "http.response.start":
                status_box[0] = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, capture)
        finally:
            code = status_box[0]
            route = scope.get("route")
            template = getattr(route, "path", path).removeprefix("/api")
            action = f"{scope['method']} {template}"
            outcome = "ok" if code < 400 else "denied" if code in (401, 403, 404, 429) else "failed"
            user_id = (scope.get("state") or {}).get("user_id")
            group_id = (scope.get("path_params") or {}).get("group_id")
            client = scope.get("client")
            ip = client[0] if client else "?"
            if get_settings().trust_proxy:
                for k, v in scope.get("headers", []):
                    if k == b"x-forwarded-for":
                        ip = v.decode().split(",")[0].strip() or ip
            await run_in_threadpool(_write_request_event, action, outcome, user_id, group_id, ip, code)


def purge_old(db: Session) -> int:
    cutoff = utc_now() - timedelta(days=get_settings().audit_retention_days)
    n = db.execute(delete(AuditLog).where(AuditLog.created_at < cutoff)).rowcount
    db.commit()
    return n
