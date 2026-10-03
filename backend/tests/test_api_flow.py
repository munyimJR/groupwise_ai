"""End-to-end API tests: auth, groups, invites, expenses, AI features, settlements, goals, copilot."""
from datetime import date, timedelta

from conftest import auth


def _signup(client, email, name="Test User"):
    r = client.post("/api/auth/signup", json={"email": email, "password": "correct-horse-1", "display_name": name})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_health_and_config(client):
    assert client.get("/api/health").json()["database"] is True
    cfg = client.get("/api/meta/config").json()
    assert cfg["auth"]["local"] is True and cfg["llm"]["available"] is False


def test_auth_errors(client):
    _signup(client, "dup@example.com")
    r = client.post("/api/auth/signup", json={"email": "dup@example.com", "password": "correct-horse-1", "display_name": "X"})
    assert r.status_code == 409
    r = client.post("/api/auth/login", json={"email": "dup@example.com", "password": "wrong-password"})
    assert r.status_code == 401
    assert client.get("/api/me").status_code == 401
    assert client.get("/api/me", headers=auth("not-a-token")).status_code == 401
    ok = client.post("/api/auth/login", json={"email": "dup@example.com", "password": "correct-horse-1"})
    assert ok.status_code == 200 and client.get("/api/me", headers=auth(ok.json()["access_token"])).status_code == 200


def test_group_lifecycle_and_balances(client):
    alice = _signup(client, "alice@example.com", "Alice")
    bob = _signup(client, "bob@example.com", "Bob")
    g = client.post("/api/groups", json={"name": "Roommates", "group_type": "roommates", "member_names": ["Cara"]},
                    headers=auth(alice)).json()
    gid = g["id"]
    detail = client.get(f"/api/groups/{gid}", headers=auth(alice)).json()
    code = detail["invite_code"]

    # outsiders can't see the group; invite preview is public; joining works
    assert client.get(f"/api/groups/{gid}", headers=auth(bob)).status_code == 404
    assert client.get(f"/api/invites/{code}").json()["group_name"] == "Roommates"
    assert client.post(f"/api/invites/{code}/join", json={}, headers=auth(bob)).status_code == 200
    members = client.get(f"/api/groups/{gid}", headers=auth(bob)).json()["members_detail"]
    ids = {m["display_name"]: m["id"] for m in members}
    assert set(ids) == {"Alice", "Bob", "Cara"}

    # equal split with remainder: 100.01 between 3 → shares sum exactly
    r = client.post(f"/api/groups/{gid}/expenses", headers=auth(alice), json={
        "description": "Lunch at restaurant", "amount": 100.01, "payer_member_id": ids["Alice"],
        "participant_ids": list(ids.values())})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["expense"]["category"] == "Food"
    assert sum(p["share"] for p in body["expense"]["participants"]) == 10001

    client.post(f"/api/groups/{gid}/expenses", headers=auth(bob), json={
        "description": "Uber to campus", "amount": 300, "payer_member_id": ids["Bob"],
        "participant_ids": [ids["Bob"], ids["Cara"]]})
    bal = client.get(f"/api/groups/{gid}/balances", headers=auth(alice)).json()
    nets = {m["name"]: m["net"] for m in bal["members"]}
    assert sum(nets.values()) == 0
    share = {p["name"]: p["share"] for p in body["expense"]["participants"]}
    assert sorted(share.values()) == [3333, 3334, 3334]
    assert nets["Alice"] == 10001 - share["Alice"] and nets["Bob"] == 30000 - share["Bob"] - 15000
    # applying the simplified transfers settles everyone
    for t in bal["transfers"]:
        assert client.post(f"/api/groups/{gid}/settlements", headers=auth(alice), json={
            "from_member_id": t["from_member_id"], "to_member_id": t["to_member_id"], "amount": t["amount"] / 100}
        ).status_code == 201
    after = client.get(f"/api/groups/{gid}/balances", headers=auth(alice)).json()
    assert all(m["net"] == 0 for m in after["members"]) and after["transfers"] == []

    # Bob can now leave (settled); notifications were created for Alice
    assert client.post(f"/api/groups/{gid}/leave", headers=auth(bob)).status_code == 200
    notes = client.get("/api/notifications", headers=auth(alice)).json()
    assert notes["unread"] >= 1


def test_validation_errors(client):
    tok = _signup(client, "val@example.com")
    gid = client.post("/api/groups", json={"name": "V"}, headers=auth(tok)).json()["id"]
    me = client.get(f"/api/groups/{gid}", headers=auth(tok)).json()["my_member_id"]
    r = client.post(f"/api/groups/{gid}/expenses", headers=auth(tok),
                    json={"description": "x", "amount": -5, "payer_member_id": me, "participant_ids": [me]})
    assert r.status_code == 422
    r = client.post(f"/api/groups/{gid}/expenses", headers=auth(tok),
                    json={"description": "x", "amount": 50, "payer_member_id": "nope", "participant_ids": [me]})
    assert r.status_code == 400
    # empty group: AI features return graceful states, not errors
    assert client.get(f"/api/groups/{gid}/forecast", headers=auth(tok)).json()["status"] == "insufficient_data"
    assert client.post(f"/api/groups/{gid}/copilot", headers=auth(tok), json={"question": "why?"}).status_code == 200


def test_demo_sandbox_ai_features(client, demo):
    tok = demo["access_token"]
    groups = client.get("/api/groups", headers=auth(tok)).json()
    assert len(groups) == 3
    squad = next(g for g in groups if g["name"] == "DIU CSE Squad")
    gid = squad["id"]

    dash = client.get(f"/api/groups/{gid}/dashboard", headers=auth(tok)).json()
    assert dash["health"]["status"] == "ok" and 0 <= dash["health"]["score"] <= 100
    kinds = {i["kind"] for i in dash["insights"]}
    assert {"anomaly", "forecast", "goal"} <= kinds
    assert dash["recommendation"] is not None

    # the flagship unusual expense is detected from data, with reasons
    anomalies = client.get(f"/api/groups/{gid}/anomalies", headers=auth(tok)).json()
    big = next(a for a in anomalies if a["amount"] == 1650000)
    assert big["anomaly"]["status"] == "flagged" and big["anomaly"]["score"] >= 0.6 and big["reasons"]
    r = client.post(f"/api/groups/{gid}/expenses/{big['id']}/review", headers=auth(tok), json={"action": "valid"})
    assert r.json()["anomaly"]["status"] == "valid"

    fc = client.get(f"/api/groups/{gid}/forecast?horizon=7", headers=auth(tok)).json()
    assert fc["status"] == "ok" and fc["interval"]["low"] <= fc["total"] <= fc["interval"]["high"]
    assert len(fc["daily"]) == 7

    goals = client.get(f"/api/groups/{gid}/goals", headers=auth(tok)).json()
    goal = goals[0]
    base = client.post(f"/api/groups/{gid}/what-if", headers=auth(tok), json={"goal_id": goal["goal_id"]}).json()
    cut = client.post(f"/api/groups/{gid}/what-if", headers=auth(tok),
                      json={"goal_id": goal["goal_id"], "category_changes": {"Food": -20}}).json()
    assert base["monthly_savings"] == 0
    assert cut["monthly_savings"] > 0
    assert cut["goal"]["scenario"]["projected"] > base["goal"]["scenario"]["projected"]
    more = client.post(f"/api/groups/{gid}/what-if", headers=auth(tok), json={"overall_change_pct": 20}).json()
    assert more["monthly_savings"] < 0

    dyn = client.get(f"/api/groups/{gid}/dynamics", headers=auth(tok)).json()
    assert abs(sum(m["paid_share_pct"] for m in dyn["members"]) - 100) < 0.5

    ans = client.post(f"/api/groups/{gid}/copilot", headers=auth(tok),
                      json={"question": "Why did our spending increase this month?"}).json()
    assert ans["intent"]["name"] == "spending_change" and ans["grounding"]["passed"] and ans["facts"]
    assert ans["mode"] == "template" and ans["notice"]
    adv = client.post(f"/api/groups/{gid}/copilot", headers=auth(tok), json={"question": "Should I buy bitcoin?"}).json()
    assert adv["intent"]["name"] == "advice_out_of_scope"


def test_categorize_and_correction_memory(client, demo):
    tok = demo["access_token"]
    gid = client.get("/api/groups", headers=auth(tok)).json()[0]["id"]
    r = client.post("/api/categorize", headers=auth(tok), json={"text": "Uber to campus 280", "group_id": gid}).json()
    assert r["parsed"]["amount"] == 280 and r["prediction"]["category"] == "Transport"
    me = client.get(f"/api/groups/{gid}", headers=auth(tok)).json()["my_member_id"]
    exp = client.post(f"/api/groups/{gid}/expenses", headers=auth(tok), json={
        "description": "Club mixer night", "amount": 900, "payer_member_id": me, "participant_ids": [me]}).json()
    client.post(f"/api/groups/{gid}/expenses/{exp['expense']['id']}/category", headers=auth(tok),
                json={"subcategory": "events"})
    again = client.post("/api/categorize", headers=auth(tok), json={"text": "Club mixer night", "group_id": gid}).json()
    assert again["prediction"]["subcategory"] == "events" and again["prediction"]["source"] == "feedback"


def test_goal_creation_and_contribution(client, demo):
    tok = demo["access_token"]
    gid = client.get("/api/groups", headers=auth(tok)).json()[0]["id"]
    me = client.get(f"/api/groups/{gid}", headers=auth(tok)).json()["my_member_id"]
    deadline = (date.today() + timedelta(days=90)).isoformat()
    g = client.post(f"/api/groups/{gid}/goals", headers=auth(tok),
                    json={"title": "Laptop fund", "target": 30000, "deadline": deadline})
    assert g.status_code == 201 and g.json()["status"] == "not_started"
    gid2 = g.json()["goal_id"]
    after = client.post(f"/api/groups/{gid}/goals/{gid2}/contributions", headers=auth(tok),
                        json={"member_id": me, "amount": 1500}).json()
    assert after["saved"] == 150000
