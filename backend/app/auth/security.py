"""Authentication: Supabase Auth tokens (production) + locally issued tokens (local accounts & demo sandbox).

* Supabase: access tokens are verified with the project's JWT secret (legacy HS256) or its public
  JWKS (asymmetric signing keys). The service-role key is never needed or accepted here.
* Local: passwords are hashed with scrypt; tokens are HS256 JWTs signed with JWT_SECRET.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from ..config import get_settings, utc_now
from ..db import get_db
from ..models import User

ISSUER = "groupwise-api"
_bearer = HTTPBearer(auto_error=False)


# ----------------------------------------------------------------------------- passwords
def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return "scrypt$" + base64.b64encode(salt).decode() + "$" + base64.b64encode(digest).decode()


def verify_password(password: str, stored: str | None) -> bool:
    if not stored or not stored.startswith("scrypt$"):
        return False
    _, salt_b64, digest_b64 = stored.split("$")
    digest = hashlib.scrypt(password.encode(), salt=base64.b64decode(salt_b64), n=2**14, r=8, p=1, dklen=32)
    return hmac.compare_digest(digest, base64.b64decode(digest_b64))


# ----------------------------------------------------------------------------- tokens
def issue_token(user: User) -> tuple[str, datetime]:
    settings = get_settings()
    expires = datetime.now(timezone.utc) + timedelta(hours=settings.jwt_ttl_hours)
    if user.expires_at is not None:
        expires = min(expires, user.expires_at.replace(tzinfo=timezone.utc))
    token = jwt.encode({"sub": user.id, "iss": ISSUER, "exp": expires, "iat": datetime.now(timezone.utc),
                        "provider": user.auth_provider}, settings.jwt_secret, algorithm="HS256")
    return token, expires


_jwks_client: jwt.PyJWKClient | None = None


def _verify_supabase(token: str) -> dict:
    settings = get_settings()
    global _jwks_client
    header = jwt.get_unverified_header(token)
    alg = header.get("alg", "HS256")
    if alg == "HS256":
        if not settings.supabase_jwt_secret:
            raise jwt.InvalidTokenError("HS256 Supabase token but SUPABASE_JWT_SECRET is not configured")
        return jwt.decode(token, settings.supabase_jwt_secret, algorithms=["HS256"], audience=settings.supabase_jwt_audience)
    if _jwks_client is None:
        _jwks_client = jwt.PyJWKClient(f"{settings.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json",
                                       cache_keys=True, lifespan=3600)
    key = _jwks_client.get_signing_key_from_jwt(token)
    return jwt.decode(token, key.key, algorithms=["ES256", "RS256", "EdDSA"], audience=settings.supabase_jwt_audience)


def _unauthorized(detail: str = "Your session has expired. Please sign in again.") -> HTTPException:
    return HTTPException(status.HTTP_401_UNAUTHORIZED, detail=detail, headers={"WWW-Authenticate": "Bearer"})


def get_current_user(creds: HTTPAuthorizationCredentials | None = Depends(_bearer), db: Session = Depends(get_db)) -> User:
    if creds is None or not creds.credentials:
        raise _unauthorized("Sign in to continue.")
    token = creds.credentials
    settings = get_settings()
    try:
        unverified = jwt.decode(token, options={"verify_signature": False})
    except jwt.InvalidTokenError:
        raise _unauthorized("Invalid session token.")

    if unverified.get("iss") == ISSUER:
        try:
            claims = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"], issuer=ISSUER)
        except jwt.ExpiredSignatureError:
            raise _unauthorized()
        except jwt.InvalidTokenError:
            raise _unauthorized("Invalid session token.")
        user = db.get(User, claims["sub"])
        if user is None or (user.expires_at is not None and user.expires_at < utc_now()):
            raise _unauthorized("This demo session has ended. Start a new one from the home page.")
        return user

    if settings.supabase_enabled:
        try:
            claims = _verify_supabase(token)
        except jwt.ExpiredSignatureError:
            raise _unauthorized()
        except (jwt.InvalidTokenError, jwt.PyJWKClientError):
            raise _unauthorized("Invalid session token.")
        user = db.get(User, claims["sub"])
        email = claims.get("email")
        meta = claims.get("user_metadata") or {}
        if user is None:
            name = (meta.get("display_name") or meta.get("full_name") or (email or "Member").split("@")[0])[:80]
            if email and db.query(User).filter(User.email == email).first():
                email = None  # a local account already uses this email; keep accounts separate
            user = User(id=claims["sub"], email=email, display_name=name, auth_provider="supabase")
            db.add(user)
            db.commit()
        return user
    raise _unauthorized("Invalid session token.")


# ----------------------------------------------------------------------------- rate limiting
class RateLimiter:
    """Small in-memory sliding-window limiter (per client IP + bucket)."""

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, request: Request, bucket: str, limit: int, window_seconds: int) -> None:
        ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (request.client.host if request.client else "?")
        key = f"{bucket}:{ip}"
        now = time.monotonic()
        with self._lock:
            q = self._hits[key]
            while q and now - q[0] > window_seconds:
                q.popleft()
            if len(q) >= limit:
                raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many requests — please wait a moment.")
            q.append(now)


limiter = RateLimiter()
