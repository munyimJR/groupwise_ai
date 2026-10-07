"""Mobile-wallet (MFS) integration: statement import, payment requests, sandbox checkout, signed webhook."""
from __future__ import annotations

import json
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth.security import get_current_user, limiter
from ..config import get_settings
from ..core.money import MoneyError, to_paisa
from ..db import get_db
from ..integrations.wallet import SIGNATURE_HEADER, TIMESTAMP_HEADER, StatementError, sign, verify
from ..models import GroupMember, PaymentRequest, User
from ..schemas import PaymentRequestIn, SandboxActionIn, StatementImportIn, StatementIn
from ..services.audit import audit
from ..services.expenses import ExpenseError
from ..services.wallet import (
    EventRejected,
    WalletError,
    apply_wallet_event,
    create_payment_request,
    import_statement,
    payment_request_out,
    preview_statement,
    sample_statement,
    sandbox_event,
)
from .common import GroupAccess, group_access

router = APIRouter(tags=["wallet"])

# Signs sandbox events when no shared secret is configured (sandbox only; never accepted by the public webhook).
_SANDBOX_SECRET = secrets.token_hex(32)


def _bad(exc: Exception) -> HTTPException:
    return HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/groups/{group_id}/wallet/sample-statement")
def get_sample_statement(access: GroupAccess = Depends(group_access), db: Session = Depends(get_db)) -> dict:
    members = list(db.scalars(select(GroupMember).where(GroupMember.group_id == access.group.id)))
    return {"csv": sample_statement(access.group, members, access.member),
            "label": "Synthetic sample statement (generic MFS CSV export). Not real data."}


@router.post("/groups/{group_id}/wallet/statement/preview")
def preview(body: StatementIn, request: Request, access: GroupAccess = Depends(group_access),
            db: Session = Depends(get_db)) -> dict:
    limiter.check(request, "wallet-preview", 60, 3600)
    try:
        return preview_statement(db, access.group, access.member, body.csv)
    except StatementError as exc:
        raise _bad(exc)


@router.post("/groups/{group_id}/wallet/statement/import")
def import_(body: StatementImportIn, request: Request, access: GroupAccess = Depends(group_access),
            db: Session = Depends(get_db)) -> dict:
    limiter.check(request, "wallet-import", 30, 3600)
    active = set(db.scalars(select(GroupMember.id).where(GroupMember.group_id == access.group.id,
                                                         GroupMember.status == "active")))
    if any(p not in active for p in body.participant_ids):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Split only between active members of this group.")
    try:
        result = import_statement(db, access.group, access.member, access.user.id, body.csv,
                                  [s.model_dump() for s in body.selections], body.participant_ids)
    except (StatementError, WalletError, ExpenseError) as exc:
        db.rollback()
        raise _bad(exc)
    db.commit()
    return result


@router.post("/groups/{group_id}/wallet/payment-requests", status_code=201)
def new_payment_request(body: PaymentRequestIn, request: Request, access: GroupAccess = Depends(group_access),
                        db: Session = Depends(get_db)) -> dict:
    limiter.check(request, "wallet-pay", 30, 3600)
    payer = access.member
    if body.payer_member_id and body.payer_member_id != access.member.id:
        # A money request: someone else pays, and only ever to the person asking.
        if body.purpose != "settlement" or body.payee_member_id != access.member.id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="You can only request money owed to you.")
        payer = db.get(GroupMember, body.payer_member_id)
        if payer is None or payer.group_id != access.group.id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Choose a member of this group.")
    try:
        pr = create_payment_request(db, access.group, payer, access.user.id, body.purpose,
                                    to_paisa(body.amount), body.payee_member_id, body.goal_id)
    except (MoneyError, WalletError) as exc:
        db.rollback()
        raise _bad(exc)
    db.commit()
    return payment_request_out(db, pr, access.user.id)


def _request_for_member(db: Session, request_id: str, user: User) -> PaymentRequest:
    pr = db.get(PaymentRequest, request_id)
    if pr is not None:
        group_access(pr.group_id, user, db)  # 404 unless the caller is an active member of that group
        return pr
    raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Payment request not found.")


@router.get("/wallet/payment-requests/{request_id}")
def get_payment_request(request_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    pr = _request_for_member(db, request_id, user)
    out = payment_request_out(db, pr, user.id)
    db.commit()  # persists an "expired" transition, if any
    return out


@router.post("/wallet/payment-requests/{request_id}/sandbox")
def sandbox_checkout(request_id: str, body: SandboxActionIn, user: User = Depends(get_current_user),
                     db: Session = Depends(get_db)) -> dict:
    """The sandbox plays the wallet: it signs the same event a real provider would send to the webhook."""
    if not get_settings().wallet_sandbox_enabled:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Wallet sandbox is disabled.")
    pr = _request_for_member(db, request_id, user)
    if not payment_request_out(db, pr, user.id)["can_approve"]:
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            detail="Only the person paying can approve this payment, and only while it is pending.")
    raw = json.dumps(sandbox_event(pr, body.action == "approve")).encode()
    secret = get_settings().wallet_webhook_secret or _SANDBOX_SECRET
    ts, sig = sign(raw, secret)
    if not verify(raw, secret, ts, sig):  # same verification path as the public webhook
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not sign the sandbox event.")
    try:
        apply_wallet_event(db, json.loads(raw))
    except EventRejected as exc:
        db.rollback()
        raise HTTPException(exc.status_code, detail=str(exc))
    db.commit()
    return payment_request_out(db, pr, user.id)


@router.post("/integrations/wallet/webhook")
async def wallet_webhook(request: Request, db: Session = Depends(get_db)) -> dict:
    """Signed payment events from the wallet provider (HMAC-SHA256 over "<timestamp>.<raw body>")."""
    secret = get_settings().wallet_webhook_secret
    if not secret:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="Wallet webhooks are not configured.")
    raw = await request.body()
    if len(raw) > 10_000 or not verify(raw, secret, request.headers.get(TIMESTAMP_HEADER),
                                       request.headers.get(SIGNATURE_HEADER)):
        audit(db, "wallet_webhook", request=request, outcome="denied", commit=True, reason="bad_signature")
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired signature.")
    try:
        event = json.loads(raw)
        if not isinstance(event, dict):
            raise ValueError
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Body must be a JSON object.")
    try:
        pr = apply_wallet_event(db, event)
    except EventRejected as exc:
        db.rollback()
        audit(db, "wallet_webhook", request=request, outcome="failed", commit=True,
              reference=str(event.get("reference"))[:40], reason=str(exc)[:120])
        raise HTTPException(exc.status_code, detail=str(exc))
    audit(db, "wallet_webhook", request=request, group_id=pr.group_id, reference=pr.reference, status=pr.status)
    db.commit()
    return {"ok": True, "reference": pr.reference, "status": pr.status}
