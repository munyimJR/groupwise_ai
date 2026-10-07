"""Multi-user concurrency, transaction consistency and failure recovery."""
import json
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from conftest import auth

from app.auth.security import limiter
from app.db import SessionLocal
from app.integrations.wallet import SIGNATURE_HEADER, TIMESTAMP_HEADER, sign
from app.models import Expense, Group

SECRET = "test-wallet-webhook-secret"


@pytest.fixture(autouse=True)
def _fresh_rate_limits():
    limiter._hits.clear()


def _signup(client, email, name):
    r = client.post("/api/auth/signup", json={"email": email, "password": "correct-horse-1", "display_name": name})
    return r.json()["access_token"]


def _shared_group(client, name):
    a, b = _signup(client, f"{name}-a@example.com", "Asha"), _signup(client, f"{name}-b@example.com", "Babu")
    g = client.post("/api/groups", json={"name": name, "group_type": "friends", "member_names": ["Chandra"]}, headers=auth(a)).json()
    code = client.get(f"/api/groups/{g['id']}", headers=auth(a)).json()["invite_code"]
    client.post(f"/api/invites/{code}/join", json={}, headers=auth(b))
    ids = {m["display_name"]: m["id"] for m in client.get(f"/api/groups/{g['id']}", headers=auth(a)).json()["members_detail"]}
    return g["id"], a, b, ids


def test_concurrent_writers_keep_ledger_and_cache_consistent(client):
    gid, a, b, ids = _shared_group(client, "conc")
    with SessionLocal() as db:
        v0 = db.get(Group, gid).data_version
    client.get(f"/api/groups/{gid}/dashboard", headers=auth(a))  # warm the cache before the burst

    def add(k):
        token, payer = (a, ids["Asha"]) if k % 2 else (b, ids["Babu"])
        return client.post(f"/api/groups/{gid}/expenses", headers=auth(token), json={
            "description": f"Lunch at canteen {k}", "amount": 100 + k, "payer_member_id": payer,
            "participant_ids": list(ids.values())}).status_code

    with ThreadPoolExecutor(max_workers=8) as pool:
        codes = list(pool.map(add, range(40)))
    assert codes.count(201) == 40, codes

    expected = sum(100 + k for k in range(40)) * 100
    with SessionLocal() as db:
        assert db.query(Expense).filter(Expense.group_id == gid).count() == 40
        assert db.get(Group, gid).data_version == v0 + 40          # no lost version bumps
    bal = client.get(f"/api/groups/{gid}/balances", headers=auth(a)).json()
    assert bal["total_spent"] == expected and sum(m["net"] for m in bal["members"]) == 0
    dash = client.get(f"/api/groups/{gid}/dashboard", headers=auth(b)).json()
    assert dash["spending"]["total"] == expected                  # the cache was invalidated, not stale


def test_duplicate_wallet_confirmations_at_the_same_time_record_once(client):
    gid, a, b, ids = _shared_group(client, "dup")
    pr = client.post(f"/api/groups/{gid}/wallet/payment-requests", headers=auth(a),
                     json={"purpose": "settlement", "amount": 300, "payee_member_id": ids["Babu"]}).json()
    raw = json.dumps({"event": "payment.succeeded", "reference": pr["reference"], "provider_txn_id": "MFS-RACE-1",
                      "amount_paisa": 30000, "currency": "BDT"}).encode()
    ts, sig = sign(raw, SECRET, int(time.time()))

    def deliver(_):
        return client.post("/api/integrations/wallet/webhook", content=raw, headers={
            "Content-Type": "application/json", TIMESTAMP_HEADER: ts, SIGNATURE_HEADER: sig}).status_code

    with ThreadPoolExecutor(max_workers=6) as pool:
        codes = list(pool.map(deliver, range(6)))
    assert set(codes) == {200}, codes
    settlements = client.get(f"/api/groups/{gid}/settlements", headers=auth(a)).json()
    assert len(settlements) == 1


def test_failure_mid_write_rolls_back_and_service_recovers(client, monkeypatch):
    gid, a, b, ids = _shared_group(client, "fail")
    from app.services import expenses as svc

    def boom(*args, **kwargs):
        raise RuntimeError("simulated crash after the expense row was written")

    monkeypatch.setattr(svc, "notify_members", boom)
    body = {"description": "Dinner", "amount": 500, "payer_member_id": ids["Asha"], "participant_ids": list(ids.values())}
    with pytest.raises(RuntimeError):
        client.post(f"/api/groups/{gid}/expenses", headers=auth(a), json=body)
    with SessionLocal() as db:
        assert db.query(Expense).filter(Expense.group_id == gid).count() == 0  # nothing half-written
    monkeypatch.undo()
    assert client.post(f"/api/groups/{gid}/expenses", headers=auth(a), json=body).status_code == 201
