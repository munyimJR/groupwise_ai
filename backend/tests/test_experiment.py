"""Controlled pilot experiment: random group-level arms, control sees no AI layer, activity is logged."""
import pytest
from conftest import auth
from sqlalchemy import select

from app.auth.security import limiter
from app.config import get_settings
from app.db import SessionLocal
from app.models import ActivityDay, ExperimentAssignment


@pytest.fixture
def experiment_on():
    s = get_settings()
    s.experiment_enabled = True
    limiter._hits.clear()
    yield
    s.experiment_enabled = False


def test_experiment_arms(client, experiment_on, demo):
    r = client.post("/api/auth/signup", json={"email": "x-ana@example.com", "password": "correct-horse-1", "display_name": "Ana"})
    token = r.json()["access_token"]
    arms = {}
    for i in range(12):
        g = client.post("/api/groups", json={"name": f"Pilot {i}", "group_type": "friends", "member_names": ["Bo"]},
                        headers=auth(token)).json()
        arms.setdefault(client.get(f"/api/groups/{g['id']}", headers=auth(token)).json()["experiment_arm"], g["id"])
        if len(arms) == 2:
            break
    assert set(arms) == {"control", "treatment"}

    control = arms["control"]
    members = client.get(f"/api/groups/{control}", headers=auth(token)).json()["members_detail"]
    ids = [m["id"] for m in members]
    for k in range(6):
        client.post(f"/api/groups/{control}/expenses", headers=auth(token), json={
            "description": f"Dinner at Kacchi Bhai {k}", "amount": 900 + k * 50, "payer_member_id": ids[0], "participant_ids": ids})
    dash = client.get(f"/api/groups/{control}/dashboard", headers=auth(token)).json()
    assert dash["experiment_arm"] == "control" and dash["insights"] == [] and dash["recommendation"] is None

    # demo sandboxes are never randomized and always get the full product
    demo_group = client.get("/api/groups", headers=auth(demo["access_token"])).json()[0]["id"]
    assert client.get(f"/api/groups/{demo_group}", headers=auth(demo["access_token"])).json()["experiment_arm"] == "treatment"

    with SessionLocal() as db:
        assert db.get(ExperimentAssignment, control).arm == "control"
        assert db.scalar(select(ActivityDay).where(ActivityDay.group_id == control)) is not None

    from scripts.experiment_report import collect, to_markdown
    report = collect()
    assert report["status"] == "ok" and report["groups"]["control"] >= 1 and report["groups"]["treatment"] >= 1
    assert "treatment vs control" in to_markdown(report)
