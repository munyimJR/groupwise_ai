import os
import sys
from pathlib import Path

# Isolated in-memory-like database and settings for every test run.
_DB = Path(__file__).parent / "_test.db"
for suffix in ("", "-wal", "-shm"):
    p = Path(str(_DB) + suffix)
    if p.exists():
        p.unlink()
# TEST_DATABASE_URL runs the whole suite against PostgreSQL (CI does); otherwise a throwaway SQLite file.
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{_DB.as_posix()}"
os.environ["JWT_SECRET"] = "test-secret-that-is-long-enough-for-hs256-ok"
os.environ["ANTHROPIC_API_KEY"] = ""
os.environ["SUPABASE_URL"] = ""
os.environ["WALLET_WEBHOOK_SECRET"] = "test-wallet-webhook-secret"
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

if os.environ.get("TEST_DATABASE_URL"):  # start every PostgreSQL run from an empty schema
    from app import models  # noqa: E402,F401
    from app.db import Base, engine  # noqa: E402

    Base.metadata.drop_all(engine)


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def demo(client):
    r = client.post("/api/demo/session")
    assert r.status_code == 200, r.text
    return r.json()
