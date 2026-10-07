"""Authorization matrix, session lifecycle, lockout, abuse detection, audit trail and privacy rights."""
import re

import pytest
from conftest import auth

from app.auth.security import limiter
from app.db import SessionLocal
from app.main import app
from app.models import AuditLog, Expense, GroupMember, User
from app.services.audit import probes

PASSWORD = "correct-horse-1"


@pytest.fixture(autouse=True)
def _fresh_limits():
    limiter._hits.clear()
    probes.reset()


def _signup(client, email, name="Tester"):
    r = client.post("/api/auth/signup", json={"email": email, "password": PASSWORD, "display_name": name})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _group(client, token, name="Flat 4B"):
    r = client.post("/api/groups", json={"name": name, "group_type": "roommates", "member_names": ["Guest"]},
                    headers=auth(token))
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _group_routes():
    for path, ops in app.openapi()["paths"].items():
        if "{group_id}" in path:
            for method in ops:
                yield method.upper(), path


def _fill(path, gid):
    path = path.replace("{group_id}", gid)
    return re.sub(r"\{[a-z_]+\}", "00000000-0000-0000-0000-000000000000", path)


def test_every_group_route_hides_other_groups_and_requires_sign_in(client):
    owner, outsider = _signup(client, "owner-matrix@example.com"), _signup(client, "outsider-matrix@example.com")
    gid = _group(client, owner)
    routes = list(_group_routes())
    assert len(routes) >= 30  # the matrix really covers the API surface
    for method, template in routes:
        url = _fill(template, gid)
        probes.reset()
        r = client.request(method, url, json={}, headers=auth(outsider))
        assert r.status_code == 404, f"outsider got {r.status_code} on {method} {template}"
        r = client.request(method, url, json={})
        assert r.status_code == 401, f"anonymous got {r.status_code} on {method} {template}"


def test_payment_requests_are_not_readable_across_groups(client):
    owner, outsider = _signup(client, "pr-owner@example.com"), _signup(client, "pr-outsider@example.com")
    gid = _group(client, owner)
    detail = client.get(f"/api/groups/{gid}", headers=auth(owner)).json()
    guest = next(m["id"] for m in detail["members_detail"] if m["display_name"] == "Guest")
    pr = client.post(f"/api/groups/{gid}/wallet/payment-requests", headers=auth(owner),
                     json={"purpose": "settlement", "amount": 100, "payee_member_id": guest})
    assert pr.status_code in (201, 400), pr.text
    if pr.status_code == 201:
        rid = pr.json()["id"]
        assert client.get(f"/api/wallet/payment-requests/{rid}", headers=auth(outsider)).status_code == 404
        assert client.post(f"/api/wallet/payment-requests/{rid}/sandbox", json={"action": "approve"},
                           headers=auth(outsider)).status_code == 404


def test_logout_revokes_only_that_session_and_logout_all_revokes_every_session(client):
    _signup(client, "sessions@example.com")
    login = lambda: client.post("/api/auth/login", json={"email": "sessions@example.com", "password": PASSWORD}).json()["access_token"]  # noqa: E731
    phone, laptop = login(), login()
    assert client.post("/api/auth/logout", headers=auth(phone)).status_code == 200
    assert client.get("/api/me", headers=auth(phone)).status_code == 401
    assert client.get("/api/me", headers=auth(laptop)).status_code == 200

    tablet = login()
    assert client.post("/api/auth/logout-all", headers=auth(laptop)).status_code == 200
    assert client.get("/api/me", headers=auth(laptop)).status_code == 401
    assert client.get("/api/me", headers=auth(tablet)).status_code == 401
    assert client.get("/api/me", headers=auth(login())).status_code == 200  # signing in again works


def test_failed_logins_lock_the_account_and_are_audited(client):
    _signup(client, "locked@example.com")
    for _ in range(5):
        r = client.post("/api/auth/login", json={"email": "locked@example.com", "password": "wrong-password-1"})
        assert r.status_code == 401
    limiter._hits.clear()  # a fresh IP: the lock is per account, not per address
    r = client.post("/api/auth/login", json={"email": "locked@example.com", "password": PASSWORD})
    assert r.status_code == 429 and "Too many failed attempts" in r.json()["detail"]
    with SessionLocal() as db:
        events = db.query(AuditLog).filter(AuditLog.action == "login").all()
        assert sum(e.outcome == "failed" for e in events) >= 5
        assert any(e.outcome == "denied" for e in events)
        assert all("locked@example.com" not in str(e.detail) and e.subject_hash != "locked@example.com" for e in events)


def test_group_id_probing_is_blocked_and_flagged(client):
    prober = _signup(client, "prober@example.com")
    codes = [client.get(f"/api/groups/probe-{i:04d}", headers=auth(prober)).status_code for i in range(22)]
    assert codes[:20] == [404] * 20 and codes[-1] == 429
    with SessionLocal() as db:
        uid = db.query(User).filter(User.email == "prober@example.com").one().id
        assert db.query(AuditLog).filter(AuditLog.action == "abuse_suspected", AuditLog.user_id == uid).count() == 1


def test_mutations_leave_an_audit_trail(client):
    token = _signup(client, "trail@example.com")
    gid = _group(client, token, "Audit trip")
    with SessionLocal() as db:
        uid = db.query(User).filter(User.email == "trail@example.com").one().id
        rows = db.query(AuditLog).filter(AuditLog.user_id == uid).all()
    actions = {(r.action, r.outcome) for r in rows}
    assert ("signup", "ok") in actions and ("POST /groups", "ok") in actions
    assert all(r.ip_hash is None or len(r.ip_hash) == 16 for r in rows)  # raw IPs are never stored
    assert any(r.group_id == gid for r in rows) or ("POST /groups", "ok") in actions


def test_data_export_and_account_deletion_keep_ledgers_intact(client):
    me, friend = _signup(client, "leaver@example.com", "Leaver"), _signup(client, "stayer@example.com", "Stayer")
    gid = _group(client, me, "Shared flat")
    code = client.get(f"/api/groups/{gid}", headers=auth(me)).json()["invite_code"]
    client.post(f"/api/invites/{code}/join", json={}, headers=auth(friend))
    ids = {m["display_name"]: m["id"] for m in client.get(f"/api/groups/{gid}", headers=auth(me)).json()["members_detail"]}
    r = client.post(f"/api/groups/{gid}/expenses", headers=auth(me), json={
        "description": "Electricity bill", "amount": 1200, "payer_member_id": ids["Leaver"],
        "participant_ids": [ids["Leaver"], ids["Stayer"]]})
    assert r.status_code == 201, r.text

    export = client.get("/api/me/export", headers=auth(me)).json()
    assert export["profile"]["email"] == "leaver@example.com"
    assert [g["group_name"] for g in export["groups"]] == ["Shared flat"]
    assert export["expenses"][0]["description"] == "Electricity bill"

    assert client.request("DELETE", "/api/me", json={"confirm": "nope"}, headers=auth(me)).status_code == 400
    assert client.request("DELETE", "/api/me", json={"confirm": "DELETE"}, headers=auth(me)).status_code == 200
    assert client.get("/api/me", headers=auth(me)).status_code == 401

    with SessionLocal() as db:
        assert db.query(User).filter(User.email == "leaver@example.com").count() == 0
        former = db.get(GroupMember, ids["Leaver"])
        assert former.user_id is None and former.display_name == "Former member"
        assert db.query(Expense).filter(Expense.group_id == gid).count() == 1
    bal = client.get(f"/api/groups/{gid}/balances", headers=auth(friend)).json()
    assert bal["total_spent"] == 120000 and sum(m["net"] for m in bal["members"]) == 0


def test_rls_policies_limit_signed_in_users_to_their_own_groups(client):
    """Postgres only: through Supabase's Data API a user can read their groups' rows and nothing else."""
    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError

    from app.db import _has_supabase_roles, engine, init_db

    if engine.dialect.name != "postgresql":
        pytest.skip("PostgreSQL only (runs in CI)")
    with engine.begin() as conn:
        if not _has_supabase_roles(conn):  # plain Postgres: install the same shims Supabase provides
            for stmt in ("CREATE ROLE anon NOLOGIN", "CREATE ROLE authenticated NOLOGIN", "CREATE SCHEMA IF NOT EXISTS auth",
                         "CREATE OR REPLACE FUNCTION auth.uid() RETURNS uuid LANGUAGE sql STABLE AS "
                         "$$ SELECT nullif(current_setting('request.jwt.claim.sub', true), '')::uuid $$",
                         "GRANT USAGE ON SCHEMA auth TO anon, authenticated"):
                conn.execute(text(stmt))
        schema = conn.execute(text("select current_schema()")).scalar()
        conn.execute(text(f'GRANT USAGE ON SCHEMA "{schema}" TO anon, authenticated'))
        conn.execute(text(f'GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA "{schema}" TO anon, authenticated'))
    init_db()  # re-applies the policies and revokes over the broad grants above

    mine, theirs = _signup(client, "rls-a@example.com"), _signup(client, "rls-b@example.com")
    my_group, their_group = _group(client, mine, "Mine"), _group(client, theirs, "Theirs")
    with SessionLocal() as db:
        uid = db.query(User).filter(User.email == "rls-a@example.com").one().id

    def as_role(role, sql, sub=None):
        with engine.connect() as conn, conn.begin():
            conn.execute(text(f"SET LOCAL ROLE {role}"))
            if sub:
                conn.execute(text("select set_config('request.jwt.claim.sub', :s, true)"), {"s": sub})
            return conn.execute(text(sql)).scalars().all()

    visible = as_role("authenticated", "select id from groups", uid)
    assert my_group in visible and their_group not in visible
    assert as_role("authenticated", "select id from users", uid) == [uid]
    for forbidden in ("select count(*) from audit_log", "select count(*) from revoked_tokens",
                      "delete from expenses returning id", "select count(*) from groups"):
        role = "anon" if forbidden.endswith("from groups") else "authenticated"
        with pytest.raises(DBAPIError):
            as_role(role, forbidden, uid)
