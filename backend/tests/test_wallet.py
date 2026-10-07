"""Mobile-wallet integration: statement parsing and import, payment requests, sandbox and signed webhook."""
import json
import time

import pytest
from conftest import auth

from app.auth.security import limiter
from app.integrations.wallet import SIGNATURE_HEADER, TIMESTAMP_HEADER, parse_statement, sign, verify

SECRET = "test-wallet-webhook-secret"


@pytest.fixture(autouse=True)
def _fresh_rate_limits():
    """Every test client shares one IP; keep the signup limit from other test modules out of these tests."""
    limiter._hits.clear()


def _signup(client, email, name):
    r = client.post("/api/auth/signup", json={"email": email, "password": "correct-horse-1", "display_name": name})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _group(client, owner, joiner, name):
    g = client.post("/api/groups", json={"name": name, "group_type": "friends", "member_names": ["Cara"]},
                    headers=auth(owner)).json()
    code = client.get(f"/api/groups/{g['id']}", headers=auth(owner)).json()["invite_code"]
    assert client.post(f"/api/invites/{code}/join", json={}, headers=auth(joiner)).status_code == 200
    members = client.get(f"/api/groups/{g['id']}", headers=auth(owner)).json()["members_detail"]
    return g["id"], {m["display_name"]: m["id"] for m in members}


def test_parser_reads_different_wallet_layouts():
    a = parse_statement("Date,Time,Transaction Type,To/From,Details,Amount (BDT),TrxID\n"
                        "06/10/2026,08:30 PM,Payment,Kacchi Bhai,Dinner,-1680.00,ABC123\n"
                        '05/10/2026,01:15 PM,Bill Pay,DESCO,Electricity,"-1,780.00",DEF456\n'
                        "05/10/2026,09:00 AM,Received Money,Rony,Snacks,300.00,GHI789\n")
    assert [(r.txn_id, r.kind, r.direction, r.amount_paisa) for r in a] == [
        ("ABC123", "payment", "out", 168000), ("DEF456", "bill_pay", "out", 178000), ("GHI789", "received", "in", 30000)]
    b = parse_statement("Transaction ID;Date;Type;Account;Debit;Credit\n"
                        "X1;2026-10-01 10:00;Merchant Payment;Shwapno;1260;\nX2;2026-10-02 11:00;Cash In;Agent;;5000\n")
    assert [(r.kind, r.direction, r.amount_paisa) for r in b] == [("payment", "out", 126000), ("cash_in", "in", 500000)]


def test_signature_verification():
    body = b'{"reference":"GW-TEST"}'
    ts, sig = sign(body, SECRET)
    assert verify(body, SECRET, ts, sig)
    assert not verify(body + b" ", SECRET, ts, sig)            # tampered body
    assert not verify(body, "other-secret", ts, sig)            # wrong key
    old_ts, old_sig = sign(body, SECRET, int(time.time()) - 3600)
    assert not verify(body, SECRET, old_ts, old_sig)            # replay of an old event


def test_statement_preview_and_import(client):
    alice = _signup(client, "w-alice@example.com", "Alice")
    bob = _signup(client, "w-bob@example.com", "Bob")
    gid, ids = _group(client, alice, bob, "Wallet flat")
    csv = ("Date,Time,Transaction Type,To/From,Details,Amount (BDT),TrxID\n"
           "06/10/2026,08:30 PM,Payment,Kacchi Bhai,Dinner for the group,-1500.00,T1\n"
           "05/10/2026,01:15 PM,Bill Pay,DESCO,Electricity bill,-1800.00,T2\n"
           "05/10/2026,11:00 AM,Mobile Recharge,Grameenphone,Recharge,-149.00,T3\n"
           "04/10/2026,10:00 AM,Send Money,Bob (01712-XXXXXX),Paid back,-600.00,T4\n"
           "04/10/2026,09:00 AM,Received Money,Bob (01712-XXXXXX),Snacks,300.00,T5\n"
           "03/10/2026,07:00 PM,Send Money,Ammu (01556-XXXXXX),Family,-1500.00,T6\n")
    r = client.post(f"/api/groups/{gid}/wallet/statement/preview", json={"csv": csv}, headers=auth(alice))
    assert r.status_code == 200, r.text
    items = {i["txn_id"]: i for i in r.json()["items"]}
    assert items["T1"]["suggestion"] == "expense" and items["T1"]["category"] == "Food"
    assert items["T2"]["suggestion"] == "expense" and items["T2"]["category"] == "Utilities"
    assert items["T3"]["suggestion"] == "skip"                       # personal recharge
    assert items["T4"]["suggestion"] == "settlement" and items["T4"]["to_member_id"] == ids["Bob"]
    assert items["T5"]["suggestion"] == "skip" and items["T6"]["suggestion"] == "skip"

    everyone = list(ids.values())
    sel = [{"txn_id": "T1", "action": "expense"}, {"txn_id": "T2", "action": "expense"},
           {"txn_id": "T4", "action": "settlement", "to_member_id": ids["Bob"]},
           {"txn_id": "T5", "action": "expense"}]                    # incoming money can't become an expense
    r = client.post(f"/api/groups/{gid}/wallet/statement/import",
                    json={"csv": csv, "selections": sel, "participant_ids": everyone}, headers=auth(alice))
    assert r.status_code == 200, r.text
    assert r.json() | {"flagged": 0} == {"expenses": 2, "settlements": 1, "skipped": 1, "flagged": 0}

    bal = client.get(f"/api/groups/{gid}/balances", headers=auth(alice)).json()
    alice_net = next(m["net"] for m in bal["members"] if m["member_id"] == ids["Alice"])
    # Alice paid 3,300 and owes a third (1,100) of it, then sent Bob 600 → net +2,200 + 600
    assert alice_net == 330000 - 110000 + 60000
    assert sum(m["net"] for m in bal["members"]) == 0

    again = client.post(f"/api/groups/{gid}/wallet/statement/preview", json={"csv": csv}, headers=auth(alice)).json()
    assert {i["txn_id"] for i in again["items"] if i["already_imported"]} == {"T1", "T2", "T4"}
    r = client.post(f"/api/groups/{gid}/wallet/statement/import",
                    json={"csv": csv, "selections": sel[:3], "participant_ids": everyone}, headers=auth(alice))
    assert r.json()["expenses"] == 0 and r.json()["skipped"] == 3   # no double counting

    bad = client.post(f"/api/groups/{gid}/wallet/statement/preview", json={"csv": "hello,world\n1,2\n"},
                      headers=auth(alice))
    assert bad.status_code == 400


def test_payment_request_sandbox_and_goal(client):
    alice = _signup(client, "p-alice@example.com", "Alice")
    bob = _signup(client, "p-bob@example.com", "Bob")
    gid, ids = _group(client, alice, bob, "Pay flat")
    client.post(f"/api/groups/{gid}/expenses", headers=auth(bob), json={
        "description": "Groceries at Shwapno", "amount": 1000, "payer_member_id": ids["Bob"],
        "participant_ids": [ids["Alice"], ids["Bob"]]})

    pr = client.post(f"/api/groups/{gid}/wallet/payment-requests", headers=auth(alice),
                     json={"purpose": "settlement", "amount": 500, "payee_member_id": ids["Bob"]})
    assert pr.status_code == 201, pr.text
    pr = pr.json()
    assert pr["status"] == "pending" and pr["reference"].startswith("GW-") and pr["can_approve"]
    # only the payer can approve; outsiders can't even see it
    assert client.post(f"/api/wallet/payment-requests/{pr['id']}/sandbox", json={"action": "approve"},
                       headers=auth(bob)).status_code == 403
    outsider = _signup(client, "p-eve@example.com", "Eve")
    assert client.get(f"/api/wallet/payment-requests/{pr['id']}", headers=auth(outsider)).status_code == 404

    done = client.post(f"/api/wallet/payment-requests/{pr['id']}/sandbox", json={"action": "approve"},
                       headers=auth(alice))
    assert done.status_code == 200, done.text
    assert done.json()["status"] == "paid" and done.json()["provider_txn_id"].startswith("SBX")
    bal = client.get(f"/api/groups/{gid}/balances", headers=auth(alice)).json()
    assert all(m["net"] == 0 for m in bal["members"] if m["member_id"] in (ids["Alice"], ids["Bob"]))
    assert client.post(f"/api/wallet/payment-requests/{pr['id']}/sandbox", json={"action": "approve"},
                       headers=auth(alice)).status_code == 403   # no longer pending

    goal = client.post(f"/api/groups/{gid}/goals", headers=auth(alice),
                       json={"title": "Trip fund", "target": 5000, "deadline": "2030-01-01"}).json()
    gp = client.post(f"/api/groups/{gid}/wallet/payment-requests", headers=auth(alice),
                     json={"purpose": "goal_contribution", "amount": 750, "goal_id": goal["goal_id"]}).json()
    client.post(f"/api/wallet/payment-requests/{gp['id']}/sandbox", json={"action": "approve"}, headers=auth(alice))
    assert client.get(f"/api/groups/{gid}/goals/{goal['goal_id']}", headers=auth(alice)).json()["saved"] == 75000

    declined = client.post(f"/api/groups/{gid}/wallet/payment-requests", headers=auth(alice),
                           json={"purpose": "settlement", "amount": 10, "payee_member_id": ids["Bob"]}).json()
    r = client.post(f"/api/wallet/payment-requests/{declined['id']}/sandbox", json={"action": "decline"},
                    headers=auth(alice))
    assert r.json()["status"] == "cancelled"


def test_money_requests(client):
    alice = _signup(client, "r-alice@example.com", "Alice")
    bob = _signup(client, "r-bob@example.com", "Bob")
    gid, ids = _group(client, alice, bob, "Request flat")

    def request(token, payer, payee, amount=100):
        return client.post(f"/api/groups/{gid}/wallet/payment-requests", headers=auth(token), json={
            "purpose": "settlement", "amount": amount, "payer_member_id": payer, "payee_member_id": payee})

    # you can only ask for money owed to you
    assert request(bob, ids["Alice"], ids["Cara"]).status_code == 400
    # Alice uses the app: only she approves, in her own wallet
    r = request(bob, ids["Alice"], ids["Bob"]).json()
    assert r["is_request"] and not r["can_approve"]
    assert client.post(f"/api/wallet/payment-requests/{r['id']}/sandbox", json={"action": "approve"},
                       headers=auth(bob)).status_code == 403
    assert client.get(f"/api/wallet/payment-requests/{r['id']}", headers=auth(alice)).json()["approve_as"] == "payer"
    # Cara is not on the app: in the sandbox, the requester simulates her approval
    c = request(bob, ids["Cara"], ids["Bob"], 120).json()
    assert c["approve_as"] == "simulate_friend"
    done = client.post(f"/api/wallet/payment-requests/{c['id']}/sandbox", json={"action": "approve"}, headers=auth(bob))
    assert done.json()["status"] == "paid"
    s = client.get(f"/api/groups/{gid}/settlements", headers=auth(bob)).json()
    assert s[0]["from_member_id"] == ids["Cara"] and s[0]["to_member_id"] == ids["Bob"] and s[0]["amount"] == 12000


def test_signed_webhook(client):
    alice = _signup(client, "h-alice@example.com", "Alice")
    bob = _signup(client, "h-bob@example.com", "Bob")
    gid, ids = _group(client, alice, bob, "Hook flat")
    pr = client.post(f"/api/groups/{gid}/wallet/payment-requests", headers=auth(alice),
                     json={"purpose": "settlement", "amount": 250, "payee_member_id": ids["Bob"]}).json()

    def post(event, secret=SECRET, ts=None):
        raw = json.dumps(event).encode()
        t, s = sign(raw, secret, ts)
        return client.post("/api/integrations/wallet/webhook", content=raw,
                           headers={"Content-Type": "application/json", TIMESTAMP_HEADER: t, SIGNATURE_HEADER: s})

    ok = {"event": "payment.succeeded", "reference": pr["reference"], "provider_txn_id": "MFS123",
          "amount_paisa": 25000, "currency": "BDT"}
    assert post(ok, secret="wrong").status_code == 401
    assert post(ok, ts=int(time.time()) - 3600).status_code == 401
    assert post({**ok, "amount_paisa": 99}).status_code == 409
    assert post({**ok, "reference": "GW-NOPE0000"}).status_code == 404
    first = post(ok)
    assert first.status_code == 200 and first.json()["status"] == "paid"
    assert post(ok).status_code == 200                               # duplicate delivery is idempotent
    assert post({**ok, "provider_txn_id": "OTHER"}).status_code == 409
    settlements = client.get(f"/api/groups/{gid}/settlements", headers=auth(alice)).json()
    assert len(settlements) == 1 and "MFS123" in settlements[0]["note"]
